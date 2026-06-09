from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class Skill(models.Model):
    name = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=50, blank=True, default='')

    def __str__(self):
        return self.name

class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    theme_preference = models.CharField(max_length=20, default='dark', choices=[
        ('light', 'Light Theme'),
        ('dark', 'Dark Theme'),
        ('glass', 'Glass Theme'),
        ('neon', 'Neon Theme'),
        ('cyberpunk', 'Cyberpunk Theme')
    ])
    email_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    verification_code_expires = models.DateTimeField(blank=True, null=True)
    reset_pin = models.CharField(max_length=6, blank=True, null=True)
    reset_pin_expires = models.DateTimeField(blank=True, null=True)
    two_factor_enabled = models.BooleanField(default=False)
    ai_memory_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}'s settings"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, default='')
    profile_image = models.ImageField(default='profile_pics/default_profile.png', upload_to='profile_pics')
    cover_image = models.ImageField(upload_to='cover_pics/', blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, default='')
    is_private = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)
    # Developer specific extensions
    is_verified = models.BooleanField(default=False)
    github_username = models.CharField(max_length=100, blank=True, default='')
    skills = models.ManyToManyField(Skill, blank=True, related_name='profiles')
    portfolio_url = models.URLField(blank=True, default='')
    profile_views = models.PositiveIntegerField(default=0)
    reach = models.PositiveIntegerField(default=0)
    is_creator = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s Profile"

class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following_relations')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follower_relations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['follower', 'following'], name='unique_followers')
        ]
        indexes = [
            models.Index(fields=['follower', 'created_at']),
            models.Index(fields=['following', 'created_at']),
        ]

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('follow', 'Follow'),
        ('follow_request', 'Follow Request'),
        ('follow_accept', 'Follow Accept'),
        ('message', 'Message'),
        ('mention', 'Mention'),
        ('story_reaction', 'Story Reaction'),
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_sent')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_received')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    post = models.ForeignKey('posts.Post', on_delete=models.CASCADE, blank=True, null=True, related_name='notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['receiver', 'is_read', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]

    def __str__(self):
        return f"{self.sender.username} -> {self.notification_type} -> {self.receiver.username}"

class ChatRoom(models.Model):
    title = models.CharField(max_length=100, blank=True, default='')
    room_type = models.CharField(max_length=20, default='direct', choices=[
        ('direct', 'Direct Message'),
        ('group', 'Group Chat')
    ])
    avatar = models.ImageField(upload_to='group_avatars/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_rooms')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Room {self.id} ({self.room_type}) - {self.title}"

class GroupMember(models.Model):
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='room_memberships')
    role = models.CharField(max_length=20, default='member', choices=[
        ('admin', 'Admin'),
        ('member', 'Member')
    ])
    joined_at = models.DateTimeField(auto_now_add=True)
    is_archived = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['chat_room', 'user'], name='unique_group_members')
        ]
        indexes = [
            models.Index(fields=['user', 'is_archived', 'is_pinned']),
            models.Index(fields=['chat_room', 'user']),
        ]

    def __str__(self):
        return f"{self.user.username} in Room {self.chat_room.id}"

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    body = models.TextField(blank=True, default='')
    is_read = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default='sent', choices=[
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('seen', 'Seen')
    ])
    
    # Attachments
    file_attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True)
    file_type = models.CharField(max_length=20, default='text', choices=[
        ('text', 'Text Message'),
        ('image', 'Image Attachment'),
        ('video', 'Video Attachment'),
        ('audio', 'Audio/Voice Message'),
        ('file', 'Document/File')
    ])

    # Threading and Forwarding
    parent_message = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    is_forwarded = models.BooleanField(default=False)

    # Deletions
    is_deleted_everyone = models.BooleanField(default=False)
    deleted_by_users = models.ManyToManyField(User, related_name='deleted_messages', blank=True)

    # Chat management features
    starred_by_users = models.ManyToManyField(User, related_name='starred_messages', blank=True)
    is_pinned = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['receiver', 'status', 'created_at']),
            models.Index(fields=['chat_room', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]

    def save(self, *args, **kwargs):
        if self.status == 'seen':
            self.is_read = True
        elif self.is_read:
            self.status = 'seen'
        super().save(*args, **kwargs)

    def __str__(self):
        dest = self.chat_room.title if self.chat_room else (self.receiver.username if self.receiver else 'Unknown')
        return f"{self.sender.username} -> {dest}: {self.body[:25]}"

class FollowRequest(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follow_requests_sent')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follow_requests_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['sender', 'receiver'], name='unique_follow_requests')
        ]
        indexes = [
            models.Index(fields=['receiver', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]

    def __str__(self):
        return f"{self.sender.username} wants to follow {self.receiver.username}"


# ──────────────────────────────────────────────
# Story (24-hour ephemeral posts)
# ──────────────────────────────────────────────
class Story(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    story_type = models.CharField(max_length=10, default='image', choices=[
        ('text', 'Text Story'),
        ('image', 'Image Story'),
        ('video', 'Video Story'),
        ('voice', 'Voice Story')
    ])
    image = models.ImageField(upload_to='stories/', blank=True, null=True)
    video_file = models.FileField(upload_to='stories/videos/', blank=True, null=True)
    voice_file = models.FileField(upload_to='stories/voice/', blank=True, null=True)
    text_content = models.TextField(blank=True, default='')
    background_color = models.CharField(max_length=30, blank=True, default='#7c3aed')
    caption = models.CharField(max_length=250, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    viewers = models.ManyToManyField(User, related_name='viewed_stories', blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['author', 'expires_at']),
            models.Index(fields=['expires_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.pk and not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.author.username}'s story ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

# Signals to auto-create Profile & UserSettings when a new User is registered
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        UserSettings.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)
    if not hasattr(instance, 'settings'):
        UserSettings.objects.create(user=instance)
    instance.profile.save()
    instance.settings.save()

# ──────────────────────────────────────────────
# Firebase Push Notification Tokens
# ──────────────────────────────────────────────
class DeviceToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_tokens')
    token = models.CharField(max_length=512, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.username}'s Device Token"

# ──────────────────────────────────────────────
# Additional Models for Phase 1 - 7 Features
# ──────────────────────────────────────────────
class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_reactions')
    reaction = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['message', 'user'], name='unique_message_reactions')
        ]
        indexes = [
            models.Index(fields=['message', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} reacted {self.reaction} to Msg {self.message.id}"

class StoryView(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='story_views')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='story_view_records')
    reaction = models.CharField(max_length=20, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['story', 'user'], name='unique_story_views')
        ]

    def __str__(self):
        return f"{self.user.username} viewed {self.story.id}"

class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    url = models.URLField(blank=True, default='')
    github_url = models.URLField(blank=True, default='')
    image = models.ImageField(upload_to='projects/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} by {self.user.username}"

class Achievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    date = models.DateField(blank=True, null=True)
    credential_url = models.URLField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} for {self.user.username}"




class CallLog(models.Model):
    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calls_started')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calls_received')
    call_type = models.CharField(max_length=10, default='audio', choices=[('audio', 'Audio Call'), ('video', 'Video Call')])
    status = models.CharField(max_length=20, default='missed', choices=[
        ('connected', 'Connected'),
        ('missed', 'Missed'),
        ('declined', 'Declined')
    ])
    duration = models.PositiveIntegerField(default=0) # in seconds
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.call_type.title()} from {self.caller.username} to {self.receiver.username} ({self.status})"


# ──────────────────────────────────────────────
# Communities Models
# ──────────────────────────────────────────────
class Community(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=50, default="fa-users")
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(User, related_name="joined_communities", blank=True)

    class Meta:
        verbose_name_plural = "Communities"

    def __str__(self):
        return self.name


class CommunityPost(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="community_posts")
    content = models.TextField()
    image = models.ImageField(upload_to="community_posts/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Post in {self.community.name} by {self.author.username}"


# ──────────────────────────────────────────────
# Premium Features Models
# ──────────────────────────────────────────────
class PremiumUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="premium")
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    badge_style = models.CharField(
        max_length=30,
        default="gold_star",
        choices=[
            ("gold_star", "Gold Star"),
            ("diamond", "Diamond"),
            ("fire", "Fire"),
            ("shield", "Shield"),
        ],
    )

    def __str__(self):
        return f"{self.user.username}'s Premium ({self.badge_style})"

