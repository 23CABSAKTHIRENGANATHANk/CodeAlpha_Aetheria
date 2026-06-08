@echo off
REM Production Database Migration and Setup Script for Windows
REM Run this after switching to PostgreSQL

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   AETHERIA PRODUCTION DATABASE SETUP (Windows)
echo ============================================================
echo.

REM Check if .env file exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo.
    echo Create .env file with the following variables:
    echo.
    echo POSTGRES_DB=aetheria
    echo POSTGRES_USER=postgres
    echo POSTGRES_PASSWORD=your_password_here
    echo POSTGRES_HOST=localhost
    echo POSTGRES_PORT=5432
    echo.
    echo Or use DATABASE_URL for production:
    echo DATABASE_URL=postgresql://user:password@host:5432/aetheria
    echo.
    pause
    exit /b 1
)

echo [OK] Found .env file

REM Create logs directory
if not exist logs mkdir logs
echo [OK] Created logs directory

REM Run migrations
echo.
echo Running Django migrations...
python manage.py migrate
if errorlevel 1 (
    echo [ERROR] Migration failed!
    pause
    exit /b 1
)

REM Collect static files
echo.
echo Collecting static files...
python manage.py collectstatic --noinput
if errorlevel 1 (
    echo [ERROR] Static files collection failed!
    pause
    exit /b 1
)

REM Create database indexes
echo.
echo Creating database indexes...
python manage.py shell ^
    -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_receiver ON users_message(receiver_id);'); cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_chatroom ON users_message(chat_room_id);'); cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_created ON users_message(created_at);'); cursor.execute('CREATE INDEX IF NOT EXISTS idx_follow_follower ON users_follow(follower_id);'); cursor.execute('CREATE INDEX IF NOT EXISTS idx_follow_following ON users_follow(following_id);'); cursor.execute('CREATE INDEX IF NOT EXISTS idx_notification_receiver ON users_notification(receiver_id, is_read);'); cursor.execute('CREATE INDEX IF NOT EXISTS idx_post_author ON posts_post(author_id, created_at);'); cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_token_user ON users_devicetoken(user_id);'); print('Indexes created')"

echo.
echo ============================================================
echo   [OK] DATABASE SETUP COMPLETE
echo ============================================================
echo.
echo Next steps:
echo 1. Create superuser: python manage.py createsuperuser
echo 2. Test WebSocket: python manage.py runserver
echo 3. Visit http://localhost:8000 in browser
echo 4. Check logs/ directory for errors
echo.
pause
