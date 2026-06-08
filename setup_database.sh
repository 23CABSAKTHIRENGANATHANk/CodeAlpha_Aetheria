#!/bin/bash
# Production Database Migration and Setup Script
# Run this after switching to PostgreSQL

set -e

echo "═══════════════════════════════════════════════════════════"
echo "  AETHERIA PRODUCTION DATABASE SETUP"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Create .env file with the following variables:"
    echo ""
    echo "# PostgreSQL Configuration"
    echo "POSTGRES_DB=aetheria"
    echo "POSTGRES_USER=postgres"
    echo "POSTGRES_PASSWORD=your_password_here"
    echo "POSTGRES_HOST=localhost"
    echo "POSTGRES_PORT=5432"
    echo ""
    echo "# Or use DATABASE_URL for production:"
    echo "# DATABASE_URL=postgresql://user:password@host:5432/aetheria"
    exit 1
fi

echo "✓ Loading environment variables from .env"
source .env

# Create logs directory
echo "Creating logs directory..."
mkdir -p logs

# Run migrations
echo ""
echo "Running Django migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo ""
echo "Creating superuser..."
python manage.py createsuperuser || true

# Collect static files
echo ""
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create database indexes
echo ""
echo "Creating database indexes..."
python manage.py shell << EOF
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_message_receiver ON users_message(receiver_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_message_chatroom ON users_message(chat_room_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_message_created ON users_message(created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_follow_follower ON users_follow(follower_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_follow_following ON users_follow(following_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notification_receiver ON users_notification(receiver_id, is_read);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_post_author ON posts_post(author_id, created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_token_user ON users_devicetoken(user_id);")
    print("✓ Database indexes created")
EOF

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✓ DATABASE SETUP COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. Test WebSocket connection: python manage.py runserver"
echo "2. Visit http://localhost:8000 in browser"
echo "3. Check logs/ directory for any errors"
echo "4. Verify device tokens at /admin/users/devicetoken/"
echo ""
