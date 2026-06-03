from django.test import TestCase
from django.contrib.auth.models import User
from .models import Profile, Follow, Notification

class UserAppTests(TestCase):
    def setUp(self):
        # Create test users
        self.user1 = User.objects.create_user(username='alice', password='password123', email='alice@test.com')
        self.user2 = User.objects.create_user(username='bob', password='password123', email='bob@test.com')

    def test_profile_auto_created(self):
        """Test that registering a user automatically instantiates a Profile."""
        self.assertTrue(Profile.objects.filter(user=self.user1).exists())
        self.assertEqual(self.user1.profile.bio, '')
        self.assertEqual(self.user1.profile.location, '')

    def test_follow_toggle(self):
        """Test creating follow relations."""
        # Create follow relation
        follow = Follow.objects.create(follower=self.user1, following=self.user2)
        self.assertTrue(Follow.objects.filter(follower=self.user1, following=self.user2).exists())
        self.assertEqual(follow.__str__(), "alice follows bob")
        
        # Test unique constraint (cannot follow same person twice)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Follow.objects.create(follower=self.user1, following=self.user2)

    def test_notification_creation(self):
        """Test that notification instances are created correctly."""
        notif = Notification.objects.create(
            sender=self.user1,
            receiver=self.user2,
            notification_type='follow'
        )
        self.assertEqual(notif.notification_type, 'follow')
        self.assertEqual(notif.receiver, self.user2)
        self.assertFalse(notif.is_read)
        self.assertEqual(notif.__str__(), "alice -> follow -> bob")

    def test_message_sending(self):
        """Test sending direct messages between users."""
        from .models import Message
        msg = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            body="Hello Bob!"
        )
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(msg.sender, self.user1)
        self.assertEqual(msg.receiver, self.user2)
        self.assertEqual(msg.body, "Hello Bob!")
        self.assertFalse(msg.is_read)
        self.assertEqual(msg.__str__(), "alice -> bob: Hello Bob!")

    def test_follow_lists_views(self):
        """Test followers and following listing views return 200."""
        # Create follow relation
        Follow.objects.create(follower=self.user1, following=self.user2)
        
        # Log in user1
        self.client.login(username='alice', password='password123')
        
        # Test followers list page for user2
        response = self.client.get(f'/profile/{self.user2.id}/followers/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'alice')
        
        # Test following list page for user1
        response = self.client.get(f'/profile/{self.user1.id}/following/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'bob')

    def test_private_profile_follow_request(self):
        """Test follow request creation and toggle logic for private accounts."""
        from .models import FollowRequest
        
        # Set user2 to private
        profile2 = self.user2.profile
        profile2.is_private = True
        profile2.save()

        self.client.login(username='alice', password='password123')
        
        # 1. Follow private user (should create FollowRequest and Notification)
        response = self.client.post(f'/follow/{self.user2.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'requested')
        self.assertFalse(data['is_following'])
        self.assertTrue(data['is_requested'])
        self.assertTrue(FollowRequest.objects.filter(sender=self.user1, receiver=self.user2).exists())
        self.assertTrue(Notification.objects.filter(sender=self.user1, receiver=self.user2, notification_type='follow_request').exists())

        # 2. Follow private user again (should delete FollowRequest and Notification)
        response = self.client.post(f'/follow/{self.user2.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'unrequested')
        self.assertFalse(data['is_following'])
        self.assertFalse(data['is_requested'])
        self.assertFalse(FollowRequest.objects.filter(sender=self.user1, receiver=self.user2).exists())
        self.assertFalse(Notification.objects.filter(sender=self.user1, receiver=self.user2, notification_type='follow_request').exists())

    def test_accept_follow_request(self):
        """Test accepting a pending follow request."""
        from .models import FollowRequest
        
        # Set user2 to private and create a FollowRequest from user1
        self.user2.profile.is_private = True
        self.user2.profile.save()
        follow_req = FollowRequest.objects.create(sender=self.user1, receiver=self.user2)
        notif = Notification.objects.create(sender=self.user1, receiver=self.user2, notification_type='follow_request')
        
        # Log in as receiver (user2)
        self.client.login(username='bob', password='password123')
        
        # Accept follow request
        response = self.client.post(f'/follow-request/accept/{follow_req.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        # Verify changes
        self.assertFalse(FollowRequest.objects.filter(id=follow_req.id).exists())
        self.assertTrue(Follow.objects.filter(follower=self.user1, following=self.user2).exists())
        self.assertFalse(Notification.objects.filter(id=notif.id).exists())
        self.assertTrue(Notification.objects.filter(sender=self.user2, receiver=self.user1, notification_type='follow_accept').exists())

    def test_decline_follow_request(self):
        """Test declining a pending follow request."""
        from .models import FollowRequest
        
        # Set user2 to private and create a FollowRequest from user1
        self.user2.profile.is_private = True
        self.user2.profile.save()
        follow_req = FollowRequest.objects.create(sender=self.user1, receiver=self.user2)
        notif = Notification.objects.create(sender=self.user1, receiver=self.user2, notification_type='follow_request')
        
        # Log in as receiver (user2)
        self.client.login(username='bob', password='password123')
        
        # Decline follow request
        response = self.client.post(f'/follow-request/decline/{follow_req.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        # Verify changes
        self.assertFalse(FollowRequest.objects.filter(id=follow_req.id).exists())
        self.assertFalse(Follow.objects.filter(follower=self.user1, following=self.user2).exists())
        self.assertFalse(Notification.objects.filter(id=notif.id).exists())

    def test_profile_and_feed_privacy_gate(self):
        """Test that profile and feed views respect private account gates."""
        from posts.models import Post
        
        # Set user2 to private and create a post
        self.user2.profile.is_private = True
        self.user2.profile.save()
        post = Post.objects.create(author=self.user2, content="Bob's private thoughts")
        
        self.client.login(username='alice', password='password123')
        
        # 1. Profile Page: should mark as locked
        response = self.client.get(f'/profile/{self.user2.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_locked'])
        self.assertFalse(response.context['posts'])
        
        # 2. Feed Page: should exclude Bob's post
        response = self.client.get('/feed/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(post, response.context['posts'])
        
        # 3. Direct Message: can_message should be False
        response = self.client.get(f'/messages/{self.user2.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['can_message'])
        
        # 4. Message API: sending to private user should return 403
        response = self.client.post(f'/messages/send/{self.user2.id}/', {'body': 'Hey Bob'})
        self.assertEqual(response.status_code, 403)


