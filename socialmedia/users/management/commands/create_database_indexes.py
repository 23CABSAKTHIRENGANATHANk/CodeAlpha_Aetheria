"""
Management command to create critical database indexes for production performance.
Run: python manage.py create_database_indexes
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.backends.postgresql.base import DatabaseCreation
import logging

logger = logging.getLogger('django.db.backends')


class Command(BaseCommand):
    help = 'Creates critical database indexes for production performance'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting database index creation...'))
        
        # Get database engine
        db_engine = connection.settings_dict.get('ENGINE', '')
        
        if 'postgresql' not in db_engine:
            self.stdout.write(self.style.WARNING('⚠️  This command is optimized for PostgreSQL. Skipping for other databases.'))
            return
        
        indexes = [
            # Message Indexes
            ("CREATE INDEX IF NOT EXISTS idx_message_receiver ON users_message(receiver_id);",
             "Message receiver index"),
            ("CREATE INDEX IF NOT EXISTS idx_message_chatroom ON users_message(chat_room_id);",
             "Message chat room index"),
            ("CREATE INDEX IF NOT EXISTS idx_message_created ON users_message(created_at DESC);",
             "Message creation time index"),
            ("CREATE INDEX IF NOT EXISTS idx_message_status ON users_message(status);",
             "Message status index"),
            
            # Follow Indexes
            ("CREATE INDEX IF NOT EXISTS idx_follow_follower ON users_follow(follower_id);",
             "Follow follower index"),
            ("CREATE INDEX IF NOT EXISTS idx_follow_following ON users_follow(following_id);",
             "Follow following index"),
            ("CREATE INDEX IF NOT EXISTS idx_follow_unique ON users_follow(follower_id, following_id);",
             "Follow unique index"),
            
            # Notification Indexes
            ("CREATE INDEX IF NOT EXISTS idx_notification_receiver ON users_notification(receiver_id, is_read);",
             "Notification receiver and read status index"),
            ("CREATE INDEX IF NOT EXISTS idx_notification_created ON users_notification(created_at DESC);",
             "Notification creation time index"),
            ("CREATE INDEX IF NOT EXISTS idx_notification_type ON users_notification(notification_type);",
             "Notification type index"),
            
            # Post Indexes
            ("CREATE INDEX IF NOT EXISTS idx_post_author ON posts_post(author_id, created_at DESC);",
             "Post author and creation time index"),
            ("CREATE INDEX IF NOT EXISTS idx_post_created ON posts_post(created_at DESC);",
             "Post creation time index"),
            
            # Like Indexes
            ("CREATE INDEX IF NOT EXISTS idx_like_post ON posts_like(post_id);",
             "Like post index"),
            ("CREATE INDEX IF NOT EXISTS idx_like_user ON posts_like(user_id);",
             "Like user index"),
            ("CREATE INDEX IF NOT EXISTS idx_like_unique ON posts_like(post_id, user_id);",
             "Like unique index"),
            
            # Device Token Indexes
            ("CREATE INDEX IF NOT EXISTS idx_device_token_user ON users_devicetoken(user_id);",
             "Device token user index"),
            ("CREATE INDEX IF NOT EXISTS idx_device_token_token ON users_devicetoken(token);",
             "Device token value index"),
            
            # Hashtag Indexes
            ("CREATE INDEX IF NOT EXISTS idx_hashtag_name ON posts_hashtag(name);",
             "Hashtag name index"),
            
            # Bookmark Indexes
            ("CREATE INDEX IF NOT EXISTS idx_bookmark_user_post ON posts_bookmark(user_id, post_id);",
             "Bookmark user and post index"),
        ]
        
        with connection.cursor() as cursor:
            for sql, description in indexes:
                try:
                    cursor.execute(sql)
                    self.stdout.write(self.style.SUCCESS(f'✓ {description}'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'⚠️  {description}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Database indexes created successfully!'))
        self.stdout.write(self.style.SUCCESS('Run: ANALYZE; -- to update table statistics'))
