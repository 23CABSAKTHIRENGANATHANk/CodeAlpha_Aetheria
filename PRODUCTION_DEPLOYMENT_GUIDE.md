# Production Deployment Guide

## Overview

This guide covers deploying Aetheria to production on Vercel with Neon PostgreSQL.

---

## Pre-Deployment Steps

### 1. Prepare Environment Variables

Create a `.env.production` file with these variables:

```bash
# Django Settings
SECRET_KEY=your-secret-key-here-make-it-very-long-and-random
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,*.vercel.app

# Database (Neon PostgreSQL)
DATABASE_URL=postgresql://user:password@host/database?sslmode=require

# Security
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# CSRF Configuration
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Email Configuration (if needed)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Firebase (for push notifications)
FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}

# Redis (optional, for caching/real-time features)
REDIS_URL=redis://user:password@host:port

# File Storage (optional)
CLOUDINARY_URL=cloudinary://key:secret@cloud_name
```

### 2. Generate a Secure SECRET_KEY

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### 3. Test Locally with Production Settings

```bash
# Create local .env file with production values
cp .env.production .env

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Run server
DEBUG=False python manage.py runserver
```

---

## Deployment to Vercel

### 1. Create Vercel Project

```bash
# Install Vercel CLI if not already installed
npm install -g vercel

# Deploy to Vercel
vercel --prod
```

### 2. Configure Vercel Environment Variables

Via Vercel Dashboard:
1. Go to Settings → Environment Variables
2. Add all variables from `.env.production`
3. Ensure variables are available in Production

Via CLI:
```bash
vercel env add SECRET_KEY
vercel env add DATABASE_URL
# ... add all other variables
```

### 3. Configure Vercel Settings

Edit `vercel.json`:

```json
{
  "framework": "django",
  "python": {
    "version": "3.12"
  },
  "env": {
    "DEBUG": false,
    "PYTHONUNBUFFERED": "1"
  },
  "buildCommand": "pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/api"
    }
  ],
  "functions": {
    "api/index.py": {
      "runtime": "python3.12"
    }
  },
  "headers": [
    {
      "source": "/static/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
```

### 4. Deploy

```bash
# Deploy to production
vercel --prod

# Check deployment
vercel ls

# View logs
vercel logs
```

---

## Alternative: Deploy to Render

### 1. Create Render Account

Visit [https://render.com](https://render.com) and sign up.

### 2. Create PostgreSQL Database

1. Click "New +" → "PostgreSQL"
2. Choose instance type (Free tier available)
3. Copy connection string
4. Add to `DATABASE_URL` environment variable

### 3. Create Web Service

1. Click "New +" → "Web Service"
2. Connect GitHub repository
3. Configure:
   - **Name**: aetheria
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`
   - **Start Command**: `gunicorn socialmedia.wsgi:application --bind 0.0.0.0:$PORT`

### 4. Add Environment Variables

In "Environment" section:
- Add all variables from `.env.production`
- Set `ALLOWED_HOSTS` to your Render URL

### 5. Deploy

Push to GitHub and deployment will start automatically.

---

## Post-Deployment Verification

### 1. Health Checks

```bash
# Check health endpoint
curl https://yourdomain.com/

# Should return login/landing page (status 200)
```

### 2. Test Key Features

```bash
# Test login
1. Navigate to /login
2. Login with test credentials
3. Should redirect to /feed

# Test CSRF protection
1. Open browser DevTools (F12)
2. Go to Network tab
3. Make any POST request (follow, comment, etc.)
4. Check request headers for X-CSRFToken

# Test database
1. Create a new post
2. Upload an image
3. Data should be saved to Neon PostgreSQL

# Test real-time features
1. Open conversation
2. Send a message
3. Should appear in real-time if WebSocket working
```

### 3. Monitor Logs

Vercel:
```bash
vercel logs
```

Render:
- Dashboard → Service Logs

### 4. Check Performance

```bash
# Page Speed Insights
# https://pagespeed.web.dev

# Lighthouse
# Chrome DevTools → Lighthouse tab

# Check for slow queries
# Monitor logs for query time > 100ms
```

---

## Troubleshooting

### CSRF Token Errors

**Error**: "CSRF token incorrect length"

**Solution**:
1. Clear browser cache and cookies
2. Refresh page
3. Check that `SECRET_KEY` is set
4. Verify `CSRF_TRUSTED_ORIGINS` includes your domain

### Database Connection Failed

**Error**: "Connection refused" or "Authentication failed"

**Solution**:
1. Verify `DATABASE_URL` is correct
2. Check Neon PostgreSQL credentials
3. Ensure database is running
4. Check firewall/network settings

### Static Files 404

**Error**: "Static file not found"

**Solution**:
1. Run `python manage.py collectstatic --noinput`
2. Verify static files directory exists
3. Check `STATIC_URL` and `STATIC_ROOT` settings

### WebSocket Connection Failed

**Error**: "WebSocket connection failed"

**Solution**:
1. Verify WebSocket origin is allowed
2. Check `WEBSOCKET_ALLOWED_ORIGINS` setting
3. Ensure Daphne/ASGI is running
4. Check firewall for WebSocket port

---

## Scaling & Performance

### Database Optimization

```sql
-- Add indexes for frequently queried fields
CREATE INDEX idx_posts_user_id ON posts_post(user_id);
CREATE INDEX idx_posts_created_at ON posts_post(created_at DESC);
CREATE INDEX idx_follow_follower ON users_follow(follower_id);
CREATE INDEX idx_comments_post_id ON posts_comment(post_id);
```

### Caching Strategy

1. **Browser Caching**: Set long cache headers for static files
2. **Redis Caching**: Cache frequently accessed data
3. **Database Query Caching**: Use ORM select_related/prefetch_related

### Connection Pooling

For high traffic, enable pgBouncer:

```python
# In settings.py
DATABASES['default']['OPTIONS'] = {
    'connect_timeout': 10,
    'keepalives': 1,
    'keepalives_idle': 30,
}
```

---

## Monitoring & Alerts

### Set Up Monitoring

1. **Error Tracking**: Sentry
   - Add Sentry DSN to environment variables
   - Monitor errors in real-time

2. **Performance Monitoring**: New Relic or Datadog
   - Track page load times
   - Monitor database performance
   - Alert on anomalies

3. **Uptime Monitoring**: UptimeRobot or Pingdom
   - Monitor endpoint availability
   - Alert on downtime

### Key Metrics to Monitor

- Response time (p50, p95, p99)
- Error rate (%)
- Database query time (ms)
- Cache hit rate (%)
- Disk space usage
- Memory usage

---

## Backup & Recovery

### Database Backups

**Neon**:
- Automatic backups every 24 hours
- Manual backup via dashboard
- Backup retention: 7 days (free), 30 days (pro)

**Render**:
- Automatic backups included
- Access via dashboard

### Recovery Procedure

1. Verify backup availability
2. Create new database from backup
3. Update `DATABASE_URL`
4. Test thoroughly before going live

---

## Security Checklist

- ✅ `DEBUG=False` in production
- ✅ Strong `SECRET_KEY` (50+ characters)
- ✅ `SECURE_SSL_REDIRECT=True`
- ✅ `CSRF_COOKIE_SECURE=True`
- ✅ `SESSION_COOKIE_SECURE=True`
- ✅ HSTS enabled
- ✅ All secrets in environment variables
- ✅ Database credentials encrypted
- ✅ API rate limiting enabled
- ✅ Security headers configured

---

## Rollback Procedure

If deployment fails:

### Vercel
```bash
# View deployments
vercel ls

# Rollback to previous version
vercel rollback
```

### Render
1. Dashboard → Deployments
2. Click on previous deployment
3. Click "Rollback"

---

## Maintenance

### Weekly Tasks
- Review logs for errors
- Check database size growth
- Monitor cache performance

### Monthly Tasks
- Update dependencies: `pip install --upgrade pip`
- Run security scan: `pip check`
- Analyze slow queries
- Backup database

### Quarterly Tasks
- Security audit
- Performance review
- Dependency updates
- Capacity planning

---

## Support & Resources

- Django Deployment: https://docs.djangoproject.com/en/stable/howto/deployment/
- Vercel Python: https://vercel.com/docs/frameworks/django
- Render Documentation: https://render.com/docs
- Neon PostgreSQL: https://neon.tech/docs
- Daphne ASGI: https://channels.readthedocs.io/

---

**Last Updated**: 2026-06-13
**Version**: 1.0.0
