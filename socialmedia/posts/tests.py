from django.test import TestCase
from django.contrib.auth.models import User
from .models import Post, Comment, Like

class PostAppTests(TestCase):
    def setUp(self):
        # Create test users
        self.user1 = User.objects.create_user(username='alice', password='password123', email='alice@test.com')
        self.user2 = User.objects.create_user(username='bob', password='password123', email='bob@test.com')
        # Create test post
        self.post = Post.objects.create(author=self.user1, content='Hello world from Alice!')

    def test_post_creation(self):
        """Test that a post is created and saved correctly."""
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(self.post.author, self.user1)
        self.assertEqual(self.post.content, 'Hello world from Alice!')
        self.assertTrue(self.post.__str__().startswith("alice's post"))

    def test_like_toggle(self):
        """Test like creation and unique constraints."""
        like = Like.objects.create(post=self.post, user=self.user2)
        self.assertEqual(Like.objects.count(), 1)
        self.assertEqual(like.post, self.post)
        self.assertEqual(like.user, self.user2)
        
        # Test unique constraint (cannot like same post twice)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Like.objects.create(post=self.post, user=self.user2)

    def test_comment_creation(self):
        """Test comments creation on posts."""
        comment = Comment.objects.create(post=self.post, author=self.user2, comment='Awesome post Alice!')
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.author, self.user2)
        self.assertEqual(comment.comment, 'Awesome post Alice!')
        self.assertEqual(comment.__str__(), f"Comment by bob on post {self.post.id}")

    def test_post_moderation_clean(self):
        """Test creating a clean post succeeds."""
        self.client.login(username='alice', password='password123')
        response = self.client.post('/create-post/', {'content': 'This is a clean developer post!'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Post.objects.filter(content='This is a clean developer post!').exists())

    def test_post_moderation_toxic(self):
        """Test creating a toxic post gets blocked."""
        self.client.login(username='alice', password='password123')
        response = self.client.post('/create-post/', {'content': 'This is hate speech abuse idiot content!'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Post.objects.filter(content='This is hate speech abuse idiot content!').exists())

    def test_communities_list_and_detail(self):
        """Test that communities list and detail views render correctly."""
        self.client.login(username='alice', password='password123')
        
        # Test List View
        response = self.client.get('/communities/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Python Developers')
        
        # Test Detail View
        response = self.client.get('/communities/python/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Python Developers')

    def test_community_post_creation(self):
        """Test creating a post in a community (clean vs toxic)."""
        self.client.login(username='alice', password='password123')
        from users.models import Community, CommunityPost
        
        # Get python community (seeded by views)
        self.client.get('/communities/python/')
        community = Community.objects.get(slug='python')
        
        # Clean post
        response = self.client.post('/communities/python/post/', {'content': 'How do I build a REST API in Django?'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CommunityPost.objects.filter(content='How do I build a REST API in Django?').exists())
        
        # Toxic post
        response = self.client.post('/communities/python/post/', {'content': 'You are a total idiot abuse.'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CommunityPost.objects.filter(content='You are a total idiot abuse.').exists())
