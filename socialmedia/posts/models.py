from django.db import models
from django.contrib.auth.models import User
import re

# ──────────────────────────────────────────────
# Hashtag
# ──────────────────────────────────────────────
class Hashtag(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'#{self.name}'

# ──────────────────────────────────────────────
# Post
# ──────────────────────────────────────────────
class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    image = models.ImageField(upload_to='posts_images/', blank=True, null=True)
    hashtags = models.ManyToManyField(Hashtag, blank=True, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.author.username}'s post ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    def extract_hashtags(self):
        """Parse and return list of lowercase hashtag names from content."""
        return [tag.lower() for tag in re.findall(r'#(\w+)', self.content)]

    def sync_hashtags(self):
        """Parse hashtags from content and update M2M relationship."""
        tag_names = self.extract_hashtags()
        tags = []
        for name in tag_names:
            tag, _ = Hashtag.objects.get_or_create(name=name)
            tags.append(tag)
        self.hashtags.set(tags)

    @property
    def content_with_hashtag_links(self):
        import html
        from django.urls import reverse
        escaped_content = html.escape(self.content)
        def replace_tag(match):
            tag_name = match.group(1)
            url = reverse('hashtag_feed', kwargs={'tag': tag_name.lower()})
            return f'<a href="{url}" class="hashtag-link">#{tag_name}</a>'
        return re.sub(r'#(\w+)', replace_tag, escaped_content)

    def get_reaction_counts(self):
        from collections import Counter
        reactions = self.reactions.all().values_list('reaction_type', flat=True)
        counter = Counter(reactions)
        emoji_map = {
            'like':  '❤️',
            'love':  '😍',
            'laugh': '😂',
            'wow':   '😮',
            'sad':   '😢',
            'fire':  '🔥',
        }
        return {emoji_map[k]: v for k, v in counter.items() if k in emoji_map}

# ──────────────────────────────────────────────
# Comment
# ──────────────────────────────────────────────
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on post {self.post.id}"

# ──────────────────────────────────────────────
# Like
# ──────────────────────────────────────────────
class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['post', 'user'], name='unique_likes')
        ]

    def __str__(self):
        return f"{self.user.username} liked post {self.post.id}"

# ──────────────────────────────────────────────
# Bookmark (Save)
# ──────────────────────────────────────────────
class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'post'], name='unique_bookmark')
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} saved post {self.post.id}"

# ──────────────────────────────────────────────
# Reaction (emoji reactions beyond simple like)
# ──────────────────────────────────────────────
class Reaction(models.Model):
    REACTION_CHOICES = [
        ('like',  '❤️'),
        ('love',  '😍'),
        ('laugh', '😂'),
        ('wow',   '😮'),
        ('sad',   '😢'),
        ('fire',  '🔥'),
    ]
    EMOJI_MAP = {
        'like':  '❤️',
        'love':  '😍',
        'laugh': '😂',
        'wow':   '😮',
        'sad':   '😢',
        'fire':  '🔥',
    }

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reactions')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'post'], name='unique_reaction')
        ]

    def __str__(self):
        return f"{self.user.username} reacted {self.reaction_type} to post {self.post.id}"


# ──────────────────────────────────────────────
# PostImage (Multiple images per post — Carousel)
# ──────────────────────────────────────────────
class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='posts_images/')
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image {self.order} for post {self.post.id}"
