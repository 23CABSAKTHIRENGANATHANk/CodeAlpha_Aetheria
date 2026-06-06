from django.test import TestCase
from django.contrib.auth.models import User
from .models import Profile, Follow, Notification

class UserAppTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        # Create test users
        self.user1 = User.objects.create_user(username='alice', password='password123', email='alice@test.com')
        self.user2 = User.objects.create_user(username='bob', password='password123', email='bob@test.com')
        
        # Mark email verified to bypass EmailVerificationMiddleware
        self.user1.settings.email_verified = True
        self.user1.settings.save()
        self.user2.settings.email_verified = True
        self.user2.settings.save()

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

    def test_call_logging_api(self):
        """Test that calling API logs calls correctly."""
        self.client.login(username='alice', password='password123')
        response = self.client.post('/api/calls/log/', {
            'receiver_id': self.user2.id,
            'call_type': 'video',
            'status': 'connected',
            'duration': 120
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        
        from .models import CallLog
        call = CallLog.objects.get(id=data['call_id'])
        self.assertEqual(call.caller, self.user1)
        self.assertEqual(call.receiver, self.user2)
        self.assertEqual(call.call_type, 'video')
        self.assertEqual(call.status, 'connected')
        self.assertEqual(call.duration, 120)

    def test_leave_group_chat(self):
        """Test leaving a group chat room."""
        from .models import ChatRoom, GroupMember
        room = ChatRoom.objects.create(room_type='group', title='Testing Group')
        GroupMember.objects.create(chat_room=room, user=self.user1, role='admin')
        GroupMember.objects.create(chat_room=room, user=self.user2, role='member')
        
        self.client.login(username='bob', password='password123')
        response = self.client.post(f'/messages/group/leave/{room.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        self.assertFalse(GroupMember.objects.filter(chat_room=room, user=self.user2).exists())
        self.assertTrue(GroupMember.objects.filter(chat_room=room, user=self.user1).exists())

    def test_api_rate_limiting(self):
        """Test API rate limiting middleware throttling."""
        from django.core.cache import cache
        cache.clear()
        
        blocked = False
        for i in range(65):
            response = self.client.post('/api/register_device_token/', {'token': f'tok_{i}'})
            if response.status_code == 429:
                blocked = True
                break
        self.assertTrue(blocked)

    def test_change_password(self):
        """Test password change form functionality."""
        self.client.login(username='alice', password='password123')
        # Failure case - wrong old password
        response = self.client.post('/settings/password/', {
            'old_password': 'wrongpassword',
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        self.assertEqual(response.status_code, 200) # Form re-rendered
        self.assertContains(response, 'Please correct the errors below.')
        
        # Success case
        response = self.client.post('/settings/password/', {
            'old_password': 'password123',
            'new_password1': 'newpass12345',
            'new_password2': 'newpass12345'
        })
        self.assertEqual(response.status_code, 302) # Redirects to profile
        
        # Check login with new password
        self.client.logout()
        login_success = self.client.login(username='alice', password='newpass12345')
        self.assertTrue(login_success)

    def test_admin_verification_dashboard(self):
        """Test superuser verification approval dashboard."""
        profile2 = self.user2.profile
        self.assertFalse(profile2.is_verified)
        
        # Non-superuser gets redirected
        self.client.login(username='alice', password='password123')
        response = self.client.get('/verification-dashboard/')
        self.assertEqual(response.status_code, 302)
        
        # Make user1 superuser
        self.user1.is_superuser = True
        self.user1.save()
        
        # Log in again to refresh superuser status in session
        self.client.login(username='alice', password='password123')
        
        # Superuser views list
        response = self.client.get('/verification-dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'bob')
        
        # Superuser approves verification
        response = self.client.post('/verification-dashboard/', {
            'profile_id': profile2.id,
            'action': 'approve'
        })
        self.assertEqual(response.status_code, 302)
        profile2.refresh_from_db()
        self.assertTrue(profile2.is_verified)
        
        # Superuser rejects / removes verification
        response = self.client.post('/verification-dashboard/', {
            'profile_id': profile2.id,
            'action': 'reject'
        })
        self.assertEqual(response.status_code, 302)
        profile2.refresh_from_db()
        self.assertFalse(profile2.is_verified)

    def test_notifications_filtering_and_marking_read(self):
        """Test notification listing filters and read markers."""
        from posts.models import Post
        post = Post.objects.create(author=self.user1, content="Hello World")
        notif1 = Notification.objects.create(sender=self.user2, receiver=self.user1, notification_type='like', post=post)
        notif2 = Notification.objects.create(sender=self.user2, receiver=self.user1, notification_type='comment', post=post)
        notif3 = Notification.objects.create(sender=self.user2, receiver=self.user1, notification_type='follow')
        
        self.client.login(username='alice', password='password123')
        
        # 1. Test Listing with filters
        response = self.client.get('/notifications/', {'filter': 'likes'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(notif1, response.context['notifications'])
        self.assertNotIn(notif2, response.context['notifications'])
        
        response = self.client.get('/notifications/', {'filter': 'comments'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(notif2, response.context['notifications'])
        self.assertNotIn(notif1, response.context['notifications'])
        
        # 2. Test individual mark read API
        notif1.refresh_from_db()
        # Loading page auto-reads, but let's test API explicitly
        self.client.post(f'/notifications/read/{notif1.id}/')
        notif1.refresh_from_db()
        self.assertTrue(notif1.is_read)
        
        # 3. Test mark all read API
        self.client.post('/notifications/read-all/')
        self.assertFalse(Notification.objects.filter(receiver=self.user1, is_read=False).exists())

    def test_story_management(self):
        """Test story creation, listing, and deletion."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.login(username='alice', password='password123')
        
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded_image = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        
        # Create story
        response = self.client.post('/stories/create/', {
            'image': uploaded_image,
            'caption': 'My image story!'
        })
        self.assertEqual(response.status_code, 302) # Redirects to feed
        
        from .models import Story
        story = Story.objects.get(author=self.user1)
        self.assertEqual(story.story_type, 'image')
        self.assertEqual(story.caption, 'My image story!')
        self.assertFalse(story.is_expired())
        
        # View user stories via API/List
        response = self.client.get(f'/profile/{self.user1.id}/stories/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['stories']), 1)
        self.assertEqual(data['stories'][0]['caption'], 'My image story!')
        
        # Delete story
        response = self.client.post(f'/stories/{story.id}/delete/')
        self.assertEqual(response.status_code, 302) # Redirects to feed
        self.assertFalse(Story.objects.filter(id=story.id).exists())

    def test_premium_features(self):
        """Test subscribing, changing badges, and cancelling premium status."""
        self.client.login(username='alice', password='password123')
        
        # Access premium settings page
        response = self.client.get('/profile/premium/')
        self.assertEqual(response.status_code, 200)
        
        # Subscribe
        response = self.client.post('/profile/premium/', {'action': 'subscribe'})
        self.assertEqual(response.status_code, 302)
        
        from .models import PremiumUser
        premium = PremiumUser.objects.get(user=self.user1)
        self.assertTrue(premium.is_active)
        self.assertEqual(premium.badge_style, 'gold_star')
        
        # Update badge style
        response = self.client.post('/profile/premium/', {
            'action': 'update_badge',
            'badge_style': 'diamond'
        })
        self.assertEqual(response.status_code, 302)
        premium.refresh_from_db()
        self.assertEqual(premium.badge_style, 'diamond')
        
        # Cancel subscription
        response = self.client.post('/profile/premium/', {'action': 'cancel'})
        self.assertEqual(response.status_code, 302)
        premium.refresh_from_db()
        self.assertFalse(premium.is_active)


