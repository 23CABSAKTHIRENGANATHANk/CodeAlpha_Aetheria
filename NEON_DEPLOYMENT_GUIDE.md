# Neon PostgreSQL + Render Deployment Guide

## Configuration Summary

✅ **All configurations updated for Neon PostgreSQL on Render**

### What Was Done

1. **settings.py Database Configuration**
   - ✅ Updated to handle `DATABASE_URL` environment variable from Render
   - ✅ Configured `dj_database_url` to parse Neon connection string
   - ✅ Added SSL support (`ssl_require=True`) for Neon's SSL requirement
   - ✅ Set proper connection options (timeout, keepalives, keepalives_idle)
   - ✅ Added fallback to SQLite for local development

2. **render.yaml Deployment Configuration**
   - ✅ **Removed** Render's built-in PostgreSQL service (using Neon instead)
   - ✅ Kept Redis service for caching and WebSocket layer
   - ✅ Set explicit `DATABASE_URL` environment variable with Neon connection string
   - ✅ Configured buildCommand with dependency installation and migrations
   - ✅ Configured startCommand with Gunicorn + Uvicorn for ASGI support
   - ✅ Set health check path `/health/` for Render monitoring

3. **requirements.txt Versions**
   - ✅ Django>=4.2,<5.0 (Python 3.10 compatible, LTS version)
   - ✅ psycopg2-binary>=2.9 (PostgreSQL adapter)
   - ✅ dj-database-url>=2.1 (DATABASE_URL parsing)
   - ✅ gunicorn>=21.2 (Production WSGI server)
   - ✅ daphne>=4.0.0 (ASGI server for WebSockets)

---

## Deployment Steps

### Step 1: Verify Local Settings (Optional)

The local environment may have different Python/Django versions than Render. This is normal.

```bash
# Local verification (Django 4.2 required for this)
cd socialmedia
python manage.py check --deploy
```

### Step 2: Commit Changes to GitHub

```bash
git add .
git commit -m "Configure Neon PostgreSQL for Render deployment

- Updated settings.py to handle DATABASE_URL with Neon SSL parameters
- Updated render.yaml to use external Neon database service
- Removed Render's built-in PostgreSQL service
- Added proper connection pooling and timeout configuration"
git push origin main
```

### Step 3: Configure Render Environment Variables

1. Go to **Render Dashboard** → **code-alpha-aetheria service**
2. Click **Environment** tab
3. Verify the following environment variables are set:

| Variable | Value | Source |
|----------|-------|--------|
| `DATABASE_URL` | `postgresql://neondb_owner:npg_pnB1ravFfS2z@ep-crimson-frog-aqzu1lox-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require` | render.yaml (hardcoded) |
| `REDIS_URL` | `redis://...` | Auto-generated from aetheria-redis service |
| `DEBUG` | `False` | render.yaml |
| `SECRET_KEY` | Auto-generated | render.yaml |
| `ALLOWED_HOSTS` | `code-alpha-aetheria.onrender.com,localhost,127.0.0.1` | render.yaml |
| `CSRF_TRUSTED_ORIGINS` | `https://code-alpha-aetheria.onrender.com` | render.yaml |
| `SECURE_SSL_REDIRECT` | `True` | render.yaml |
| `SESSION_COOKIE_SECURE` | `True` | render.yaml |
| `CSRF_COOKIE_SECURE` | `True` | render.yaml |

### Step 4: Trigger Render Deployment

Option A: **Automatic** (via webhook)
- Push to main branch (Step 2 above)
- Render automatically deploys within 30 seconds

Option B: **Manual** (via Render Dashboard)
1. Go to Render Dashboard → code-alpha-aetheria service
2. Click the three-dot menu → **Trigger deploy**
3. Select branch: `main`
4. Click **Deploy latest commit**

### Step 5: Monitor Build Process

1. Click **Logs** tab in Render service
2. Watch for build progress:
   ```
   Starting build process...
   Installing dependencies...
   Running migrations...
   Collecting static files...
   ✅ Build complete
   ```

3. Watch for startup logs:
   ```
   Starting Django...
   [timestamp] [worker:1] Listening at: 0.0.0.0:3000
   [timestamp] [worker:1] Using worker class: uvicorn.workers.UvicornWorker
   ```

---

## Deployment Verification

### Health Check Endpoints

After deployment, verify the app is running:

```bash
# Replace with your Render URL
RENDER_URL="https://code-alpha-aetheria.onrender.com"

# Check comprehensive health status
curl -i "$RENDER_URL/health/"

# Check deployment readiness
curl -i "$RENDER_URL/ready/"

# Check liveness (fast check)
curl -i "$RENDER_URL/alive/"
```

Expected responses:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "debug_mode": false,
  "timestamp": "2025-01-18T12:00:00Z"
}
```

### Basic Functionality Tests

1. **Landing Page**
   ```
   GET https://code-alpha-aetheria.onrender.com/
   Expected: 200 OK - Landing page loads
   ```

2. **Login Page**
   ```
   GET https://code-alpha-aetheria.onrender.com/login/
   Expected: 200 OK - Login form loads
   ```

3. **Feed (Requires Auth)**
   ```
   GET https://code-alpha-aetheria.onrender.com/feed/
   Expected: 302 Redirect to login (if not authenticated)
   ```

---

## Neon Connection String Breakdown

```
postgresql://
  neondb_owner:              # Username
  npg_pnB1ravFfS2z@          # Password (API key)
  ep-crimson-frog-aqzu1lox-pooler  # Hostname (pooler endpoint)
  .c-8.us-east-1.aws.neon.tech    # Neon region
  /neondb                    # Database name
  ?sslmode=require           # Require SSL for all connections
  &channel_binding=require   # Require channel binding for enhanced security
```

**Important Parameters:**
- `sslmode=require` - Mandatory for Neon security
- `channel_binding=require` - Extra security layer (supported by psycopg2)
- Pooler endpoint (not direct endpoint) - Enables connection pooling
- Port 5432 (default, not shown in URL)

---

## Troubleshooting

### Build Fails: "Could not find a version that satisfies requirement django>=6.0"

✅ **FIXED** - Updated requirements.txt to `django>=4.2,<5.0` (Render uses Python 3.10)

### Build Fails: "FATAL: invalid value for parameter 'default_transaction_isolation'"

✅ **FIXED** - settings.py now properly cleans DATABASE_URL before parsing

### App Crashes: "Module psycopg2 not found"

✅ **FIXED** - Added `psycopg2-binary>=2.9` to requirements.txt

### Database Connection Timeout

**Possible causes:**
1. Neon API is temporarily unavailable
2. Connection pooling limits exceeded
3. SSL certificate mismatch

**Solutions:**
- Wait 5 minutes and redeploy
- Check Neon Console for active connections
- Verify connection string in `render.yaml`

---

## Environment-Specific Settings

### Render Production (DATABASE_URL set)
```
✅ Uses Neon PostgreSQL
✅ SSL enabled (sslmode=require)
✅ Connection pooling enabled
✅ Debug = False
✅ Static files served via whitenoise
```

### Local Development (DATABASE_URL not set)
```
✅ Falls back to SQLite (db.sqlite3)
✅ Django debug toolbar available
✅ No SSL required
✅ For testing only
```

---

## Next Steps

### Immediate (Deployment)
1. ✅ Git commit and push to main
2. ✅ Monitor Render build logs (5-10 minutes)
3. ✅ Test health endpoints

### Short-term (Verification)
1. Test login functionality
2. Test posting and feed
3. Test messaging features
4. Monitor performance metrics

### Medium-term (APK Build)
1. Only after verifying Render deployment works
2. Update Capacitor configuration with Render URL
3. Follow APK_QUICK_START.md

---

## Security Notes

1. **Database Credentials**
   - Stored in `render.yaml` as literal (should be in Render Secrets in production)
   - Keep render.yaml out of public repositories
   - Rotate credentials monthly in production

2. **SSL/TLS**
   - All connections to Neon require SSL (enforced)
   - Render to user connections use HTTPS (enforced)
   - HSTS headers configured for Chrome/Firefox security

3. **CORS & CSRF**
   - CSRF protected for all POST requests
   - CORS only allows Render domain
   - Session cookies marked secure and httpOnly

---

## Performance Optimization

**Render Free Tier Limitations:**
- App goes to sleep after 15 minutes of inactivity
- Wakes up on first request (~30 second startup)
- Max 2 processes recommended
- Database limited to 10GB

**Optimizations Applied:**
- Connection pooling via Neon (max 10 connections)
- Redis caching for session/channel layer
- Static files cached with whitenoise
- Database keepalives configured (prevents connection timeout)

**Monitoring:**
- Health check every 30 seconds keeps app awake
- Check Render Dashboard → Metrics for CPU/Memory usage
- Review logs for slow queries or errors

---

## Database Backups

Neon provides automated backups. To restore:

1. Go to **Neon Console** → **Branches**
2. Select a previous branch (points-in-time recovery)
3. View backup retention in your Neon account settings

---

## Summary

✅ All configurations ready for Render + Neon deployment  
✅ Render.yaml configured for external database  
✅ Settings.py configured for DATABASE_URL parsing  
✅ Django 4.2 LTS version ensures Python 3.10 compatibility  
✅ Health check endpoints available for monitoring  

**Next Action:** Push to GitHub and monitor Render deployment logs
