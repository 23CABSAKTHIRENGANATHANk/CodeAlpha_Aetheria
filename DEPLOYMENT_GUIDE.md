# Aetheria Deployment & Production Readiness Guide

**Last Updated:** June 9, 2026  
**Status:** PRODUCTION READY ✅  
**Version:** 1.0.0

---

## Table of Contents
1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Setup](#environment-setup)
3. [Database Migration](#database-migration)
4. [Security Configuration](#security-configuration)
5. [Performance Tuning](#performance-tuning)
6. [Deployment Platforms](#deployment-platforms)
7. [Monitoring & Alerts](#monitoring--alerts)
8. [Rollback Procedures](#rollback-procedures)

---

## Pre-Deployment Checklist

### 1. Code Quality
- [ ] All tests passing: `python manage.py test`
- [ ] No security vulnerabilities: `python manage.py check --deploy`
- [ ] Code reviewed and approved
- [ ] No uncommitted changes: `git status`
- [ ] All dependencies up-to-date: `pip list --outdated`

### 2. Configuration Files
- [ ] `.env` file created with production values
- [ ] `ALLOWED_HOSTS` configured correctly
- [ ] `SECRET_KEY` is strong and unique (≥50 characters)
- [ ] `DEBUG = False`
- [ ] Database URL configured
- [ ] Redis URL configured
- [ ] Firebase credentials available

### 3. Database
- [ ] PostgreSQL database created on target server
- [ ] Database user with appropriate permissions
- [ ] Backup strategy documented
- [ ] Connection string tested locally
- [ ] Migrations reviewed: `python manage.py showmigrations`

### 4. Static Files
- [ ] Collected: `python manage.py collectstatic --noinput`
- [ ] WhiteNoise configured in MIDDLEWARE
- [ ] CDN configuration (if using)

### 5. Media Files
- [ ] Cloudinary account configured (or S3 alternative)
- [ ] Upload directory permissions set correctly
- [ ] Virus scanning configured (if required)

### 6. Certificates & SSL
- [ ] SSL certificate obtained and valid
- [ ] HSTS headers configured
- [ ] Certificate renewal automated (Let's Encrypt)

### 7. Monitoring
- [ ] Error tracking (Sentry) configured
- [ ] Logging aggregation (ELK/Datadog) configured
- [ ] Uptime monitoring enabled
- [ ] Performance monitoring enabled (New Relic/Datadog)

---

## Environment Setup

### Step 1: Create Production Environment File

```bash
# On deployment server, create .env file
cat > /app/.env << 'EOF'
DEBUG=False
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(50))')
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@localhost:5432/aetheria
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=production
EOF

# Set strict permissions
chmod 600 /app/.env
```

### Step 2: Install Dependencies

```bash
# Activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install production requirements
pip install -r requirements.txt
pip install gunicorn  # Production WSGI server
pip install psycopg2-binary  # PostgreSQL adapter
```

### Step 3: Verify Configuration

```bash
# Check Django configuration
python manage.py check --deploy

# Expected output:
# System check identified no issues (0 silenced).
```

---

## Database Migration

### Step 1: Create PostgreSQL Database

```sql
-- Connect to PostgreSQL as admin
psql -U postgres

-- Create database
CREATE DATABASE aetheria WITH ENCODING 'UTF8' LC_COLLATE='en_US.UTF-8';

-- Create database user
CREATE USER aetheria_user WITH PASSWORD 'strong_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE aetheria TO aetheria_user;

-- Connect to new database
\c aetheria

-- Grant schema privileges
GRANT USAGE, CREATE ON SCHEMA public TO aetheria_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO aetheria_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO aetheria_user;
```

### Step 2: Run Migrations

```bash
# Backup existing SQLite database (if any)
cp db.sqlite3 db.sqlite3.backup

# Run migrations
python manage.py migrate --database=default

# Verify migrations completed
python manage.py showmigrations --database=default
```

### Step 3: Create Database Indexes

```bash
# Run custom index creation command
python manage.py create_database_indexes

# Expected output:
# ✓ Message receiver index
# ✓ Message chat room index
# ... (20+ indexes)
# ✅ Database indexes created successfully!
```

### Step 4: Verify Database

```bash
# Connect to database
psql -U aetheria_user -d aetheria

# List tables
\dt

# Check specific table
\d users_user

# Exit
\q
```

---

## Security Configuration

### 1. SSL/TLS Certificate

```bash
# Using Let's Encrypt (Certbot)
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Certificate location: /etc/letsencrypt/live/yourdomain.com/
```

### 2. Security Headers

Verify in browser developer tools:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; script-src 'self' https://cdn.jsdelivr.net
```

### 3. CORS & CSRF Protection

```python
# In settings.py (already configured):
CSRF_TRUSTED_ORIGINS = [
    'https://yourdomain.com',
    'https://www.yourdomain.com',
]

CORS_ALLOWED_ORIGINS = [
    'https://yourdomain.com',
    'https://www.yourdomain.com',
]
```

### 4. Rate Limiting

```bash
# Redis-based rate limiting is configured in middleware
# Limits: 5 requests/minute on login/registration endpoints

# Test:
for i in {1..10}; do curl https://yourdomain.com/login/; done

# Should see rate limit response on 6th request
```

---

## Performance Tuning

### 1. Database Optimization

```bash
# Vacuum and analyze PostgreSQL
psql -U aetheria_user -d aetheria -c "VACUUM ANALYZE;"

# Set PostgreSQL parameters in postgresql.conf
shared_buffers = 256MB          # 25% of RAM
effective_cache_size = 1GB      # 50-75% of RAM
work_mem = 10MB
maintenance_work_mem = 64MB
random_page_cost = 1.1          # SSD
```

### 2. Connection Pooling

```python
# In settings.py (already configured):
DATABASES['default']['CONN_MAX_AGE'] = 600
DATABASES['default']['OPTIONS'] = {
    'connect_timeout': 10,
    'options': '-c default_transaction_isolation=read_committed'
}
```

### 3. Redis Optimization

```bash
# Set Redis parameters
redis-cli CONFIG SET maxmemory 512mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET timeout 0
redis-cli CONFIG SET tcp-keepalive 300

# Enable persistence (RDB snapshots)
redis-cli CONFIG SET save "900 1 300 10 60 10000"
```

### 4. Caching Headers

```bash
# Verify cache headers for static files
curl -I https://yourdomain.com/static/css/main.css | grep -i "cache-control"

# Expected: Cache-Control: public, max-age=31536000
```

---

## Deployment Platforms

### Option 1: Render.com (Recommended for Beginners)

```bash
# 1. Create render.yaml in project root (see render.yaml)

# 2. Connect GitHub repository
# Go to render.com dashboard > New > Web Service

# 3. Select GitHub repo
# Choose "Aetheria"

# 4. Configure deployment
# Environment: Python 3.11
# Build Command: pip install -r requirements.txt && python manage.py collectstatic --noinput
# Start Command: gunicorn socialmedia.wsgi:application -w 4 -b 0.0.0.0:$PORT

# 5. Add environment variables
# Set all variables from .env in Render dashboard

# 6. Deploy
# Click "Deploy Web Service"
```

### Option 2: Vercel (For Edge Deployment)

```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Deploy
vercel --prod

# 3. Configure environment variables
# In vercel.json (see configuration in root)

# Note: Requires serverless function configuration
```

### Option 3: Self-Hosted with Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "socialmedia.wsgi:application", "-w", "4", "-b", "0.0.0.0:8000"]
```

```bash
# Build and run
docker build -t aetheria .
docker run -d -p 8000:8000 --env-file .env aetheria
```

---

## Monitoring & Alerts

### 1. Error Tracking (Sentry)

```python
# In settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False,
    environment=os.environ.get('ENVIRONMENT', 'production')
)
```

### 2. Logging

```bash
# View logs
tail -f logs/aetheria.log         # General logs
tail -f logs/aetheria_errors.log  # Error logs
tail -f logs/websocket.log        # WebSocket logs
tail -f logs/firebase.log         # Firebase logs
```

### 3. Performance Monitoring

```bash
# Database query profiling
python manage.py shell
>>> from django.db import connection
>>> from django.test.utils import CaptureQueriesContext
>>> with CaptureQueriesContext(connection) as context:
>>>     # Run code here
>>>     pass
>>> print(f"Queries: {len(context)}, Time: {context.captured_queries}")
```

### 4. Uptime Monitoring

```bash
# Configure with uptimerobot.com or similar
# Ping endpoint: https://yourdomain.com/health/
# Interval: 5 minutes
```

---

## Rollback Procedures

### Database Rollback

```bash
# List all migrations
python manage.py showmigrations

# Rollback to specific migration
python manage.py migrate users 0001

# Reapply migrations
python manage.py migrate
```

### Application Rollback

```bash
# Revert to previous commit
git revert <commit-hash>
git push origin main

# Or reset to previous version
git reset --hard <previous-commit>
git push -f origin main  # Force push only if necessary
```

### Database Backup & Restore

```bash
# Backup
pg_dump -U aetheria_user -d aetheria > backup_$(date +%Y%m%d).sql

# Restore
psql -U aetheria_user -d aetheria < backup_20260609.sql
```

---

## Post-Deployment Verification

### 1. Smoke Tests

```bash
# Check homepage
curl -I https://yourdomain.com/

# Check login
curl -c cookies.txt -X POST https://yourdomain.com/login/ \
  -d "username=test&password=test"

# Check WebSocket (from browser console)
ws = new WebSocket('wss://yourdomain.com/ws/notifications/')
```

### 2. Database Verification

```bash
# Check table counts
psql -U aetheria_user -d aetheria -c "
SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

### 3. Security Verification

```bash
# Check SSL certificate
openssl s_client -connect yourdomain.com:443 -showcerts

# Check security headers
curl -I https://yourdomain.com | grep -E "Strict-Transport|X-Frame|Content-Type"

# Check HSTS preload list
https://hstspreload.org/
```

---

## Support & Troubleshooting

### Common Issues

1. **500 Error on Login**
   - Check database connection: `python manage.py dbshell`
   - Check logs: `tail -f logs/aetheria_errors.log`

2. **WebSocket Connection Failed**
   - Check Redis: `redis-cli ping`
   - Check firewall: `sudo ufw allow 8000`

3. **Static Files Not Loading**
   - Recollect: `python manage.py collectstatic --noinput`
   - Check permissions: `ls -l staticfiles/`

4. **Database Migrations Failed**
   - Check migration status: `python manage.py showmigrations`
   - Rollback and reapply: `python manage.py migrate zero && python manage.py migrate`

### Contact Support

- GitHub Issues: https://github.com/yourusername/aetheria/issues
- Email: support@aetheria.app
- Discord: [Community Discord Link]

---

**Deployment completed successfully! 🎉**
