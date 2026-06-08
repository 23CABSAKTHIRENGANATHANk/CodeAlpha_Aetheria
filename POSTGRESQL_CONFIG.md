# PostgreSQL Production Database Configuration
# Add this to socialmedia/settings.py (REPLACE the current SQLite config)

# ──────────────────────────────────────────────
# DATABASE CONFIGURATION - PRODUCTION READY
# ──────────────────────────────────────────────

# PostgreSQL DATABASE (REQUIRED FOR PRODUCTION)
# This replaces the SQLite configuration

if os.environ.get('DATABASE_URL'):
    # Use environment variable for production (from platforms like Vercel, Heroku, etc)
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,  # Connection pooling
            conn_health_checks=True,  # Health checks
            ssl_require=True,  # Require SSL for security
        )
    }
    
    # Additional PostgreSQL connection settings
    DATABASES['default'].update({
        'ATOMIC_REQUESTS': False,
        'AUTOCOMMIT': True,
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c default_transaction_isolation=read_committed',
            'sslmode': 'require',
        }
    })
    
elif os.environ.get('POSTGRES_PASSWORD'):
    # Local development PostgreSQL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'aetheria'),
            'USER': os.environ.get('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
            'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'connect_timeout': 10,
                'options': '-c default_transaction_isolation=read_committed'
            }
        }
    }
    
else:
    # Fallback to SQLite for development only
    print('⚠️  WARNING: Using SQLite database. Switch to PostgreSQL for production!')
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ──────────────────────────────────────────────
# DATABASE INDEXES & OPTIMIZATION
# ──────────────────────────────────────────────

# These indexes should be created after migration:
# python manage.py migrate
# python manage.py shell
# >>> from django.db import connection
# >>> with connection.cursor() as cursor:
# >>>     cursor.execute("CREATE INDEX IF NOT EXISTS idx_message_receiver ON users_message(receiver_id);")
# >>>     cursor.execute("CREATE INDEX IF NOT EXISTS idx_message_chatroom ON users_message(chat_room_id);")
# >>>     cursor.execute("CREATE INDEX IF NOT EXISTS idx_message_created ON users_message(created_at);")
# >>>     cursor.execute("CREATE INDEX IF NOT EXISTS idx_follow_follower ON users_follow(follower_id);")
# >>>     cursor.execute("CREATE INDEX IF NOT EXISTS idx_follow_following ON users_follow(following_id);")
# >>>     cursor.execute("CREATE INDEX IF NOT EXISTS idx_notification_receiver ON users_notification(receiver_id, is_read);")
# >>>     cursor.execute("CREATE INDEX IF NOT EXISTS idx_post_author ON posts_post(author_id, created_at);")
# >>>     cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_token_user ON users_devicetoken(user_id);")

# ──────────────────────────────────────────────
# DATABASE BACKUP CONFIGURATION
# ──────────────────────────────────────────────

# For production, implement regular backups:
# 1. Using Django Management Command:
#    - Create a management command: python manage.py backup_database
#    
# 2. Using PostgreSQL pg_dump:
#    - pg_dump -U postgres aetheria > backup.sql
#    - Schedule with cron: 0 2 * * * pg_dump -U postgres aetheria > /backups/aetheria_$(date +%Y%m%d).sql
#
# 3. Using Cloud Storage (S3, GCS):
#    - Automatically backup to cloud storage
#
# 4. Point-in-time recovery (PITR):
#    - Enable WAL archiving for PostgreSQL
#    - Set: wal_level = replica, archive_mode = on

# ──────────────────────────────────────────────
# MIGRATION NOTES
# ──────────────────────────────────────────────

# After switching to PostgreSQL, run:
# 1. python manage.py migrate --database=default
# 2. python manage.py collectstatic --noinput
# 3. Run index creation script above
# 4. Test thoroughly before deploying to production

# ──────────────────────────────────────────────
# ENVIRONMENT VARIABLES REQUIRED
# ──────────────────────────────────────────────

# For Vercel deployment, add these to Environment Variables:
# DATABASE_URL=postgresql://user:password@host:5432/aetheria

# For local development, add to .env:
# POSTGRES_DB=aetheria
# POSTGRES_USER=postgres
# POSTGRES_PASSWORD=your_secure_password
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
