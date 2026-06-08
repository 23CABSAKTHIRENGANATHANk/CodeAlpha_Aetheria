# AETHERIA PRODUCTION IMPLEMENTATION GUIDE

**Status:** Critical Fixes Required Before Launch  
**Priority:** HIGH - Must Complete All Fixes  
**Estimated Implementation Time:** 2-3 weeks

---

## CRITICAL FIXES TO APPLY (In Priority Order)

### ✅ PHASE 1: DATABASE & CONFIGURATION (CRITICAL)

#### 1.1 Switch to PostgreSQL
**File:** `socialmedia/settings.py`  
**Status:** NEEDS IMMEDIATE ACTION

```python
# CURRENT (BROKEN FOR PRODUCTION):
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DB_PATH,
    }
}

# REPLACE WITH (see POSTGRESQL_CONFIG.md):
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True,
    )
}
```

**Action Steps:**
1. Copy configuration from `POSTGRESQL_CONFIG.md` to settings.py
2. Create PostgreSQL database (use Neon, AWS RDS, or local PostgreSQL)
3. Set `DATABASE_URL` environment variable
4. Run migrations: `python manage.py migrate`
5. Create indexes: Run script in POSTGRESQL_CONFIG.md

**Verify:**
```bash
python manage.py dbshell
\dt  # List tables
\d users_message  # Check message table
```

---

#### 1.2 Add Logging Configuration
**File:** `socialmedia/settings.py`  
**Status:** NEEDS IMPLEMENTATION

**Action Steps:**
1. Copy logging configuration from `LOGGING_CONFIG.md`
2. Append to settings.py (after DATABASE configuration)
3. Create `logs/` directory in project root
4. Test logging: `python manage.py shell`

```python
import logging
logger = logging.getLogger('aetheria')
logger.info('Test log message')
```

---

### ✅ PHASE 2: FRONTEND WEBSOCKET FIX (CRITICAL)

#### 2.1 Include WebSocket Client Library
**File:** `socialmedia/templates/base.html`  
**Status:** NEEDS IMPLEMENTATION

Add before closing `</head>` tag:
```html
<script src="{% static 'js/websocket-client.js' %}"></script>
<script src="{% static 'js/firebase-notifications.js' %}"></script>
```

**Verify:** Open browser console, should see:
```
[Aetheria] Initializing WebSocket connections...
[WebSocket] Connecting to ws://localhost:8000/ws/notifications/...
[WebSocket] Connected!
```

---

#### 2.2 Add WebSocket Status Indicator
**File:** `socialmedia/templates/base.html`  
**Status:** NEEDS IMPLEMENTATION

Add in the navigation bar:
```html
<!-- Connection Status Indicator -->
<div class="connection-status-indicator" data-ws-status="disconnected">
    <span class="connection-status-dot"></span>
    <span class="connection-status-text">Offline</span>
</div>
```

Add CSS (to `static/css/main.css`):
```css
[data-ws-status] {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
}

[data-ws-status="connected"] {
    background: #10b981;
    color: white;
}

[data-ws-status="connecting"] {
    background: #f59e0b;
    color: white;
}

[data-ws-status="reconnecting"] {
    background: #ef4444;
    color: white;
}

[data-ws-status="disconnected"] {
    background: #6b7280;
    color: white;
}

.connection-status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse-connected 2s ease-in-out infinite;
}

[data-ws-status="disconnected"] .connection-status-dot {
    animation: none;
}

@keyframes pulse-connected {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
```

---

### ✅ PHASE 3: FIREBASE NOTIFICATIONS (CRITICAL)

#### 3.1 Setup Firebase Configuration
**File:** `socialmedia/templates/base.html`  
**Status:** NEEDS IMPLEMENTATION

Add before closing `</head>` tag:
```html
<script>
    // Set Firebase configuration
    window.firebaseConfig = {
        apiKey: "{{ FIREBASE_API_KEY }}",
        authDomain: "{{ FIREBASE_AUTH_DOMAIN }}",
        projectId: "{{ FIREBASE_PROJECT_ID }}",
        storageBucket: "{{ FIREBASE_STORAGE_BUCKET }}",
        messagingSenderId: "{{ FIREBASE_MESSAGING_SENDER_ID }}",
        appId: "{{ FIREBASE_APP_ID }}",
    };
</script>
```

**Action Steps:**
1. Get values from Firebase Console
2. Add to Django settings as context variables
3. Update base.html template context processor

---

#### 3.2 Update Device Token API
**File:** `socialmedia/users/views.py`  
**Status:** ALREADY IMPLEMENTED ✓

The endpoint already exists at `api_register_device_token` (line 748).  
Verify it's working:
```bash
curl -X POST http://localhost:8000/api/register_device_token/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: TOKEN" \
  -d '{"token":"fake_token_123"}'
```

---

#### 3.3 Add Notification Toast Container
**File:** `socialmedia/templates/base.html`  
**Status:** NEEDS IMPLEMENTATION

Add in body (after opening `<body>` tag):
```html
<!-- Notification Toast Container -->
<div id="notification-toast-container" class="notification-toast-container"></div>
```

Add CSS (to `static/css/main.css`):
```css
.notification-toast-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-width: 400px;
}

.notification-toast {
    background: white;
    border-radius: 8px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    animation: slideIn 0.3s ease-out;
}

.notification-toast.dismissing {
    animation: slideOut 0.3s ease-out;
}

.notification-toast-content {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
}

.notification-icon {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    object-fit: cover;
}

.notification-text {
    flex: 1;
}

.notification-title {
    display: block;
    font-weight: 600;
    color: #1f2937;
    margin-bottom: 2px;
}

.notification-body {
    margin: 0;
    font-size: 14px;
    color: #6b7280;
}

.notification-close {
    background: none;
    border: none;
    font-size: 20px;
    cursor: pointer;
    color: #d1d5db;
    padding: 0;
    margin-left: 8px;
    flex-shrink: 0;
}

.notification-close:hover {
    color: #9ca3af;
}

@keyframes slideIn {
    from {
        transform: translateX(400px);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

@keyframes slideOut {
    from {
        transform: translateX(0);
        opacity: 1;
    }
    to {
        transform: translateX(400px);
        opacity: 0;
    }
}

@media (max-width: 480px) {
    .notification-toast-container {
        left: 10px;
        right: 10px;
        max-width: none;
    }
}
```

---

### ✅ PHASE 4: ANDROID CONFIGURATION (CRITICAL)

#### 4.1 Create Notification Channels
**File:** `android/app/src/main/java/com/aetheria/app/NotificationChannels.java`  
**Status:** ALREADY CREATED ✓

File created. Now integrate with MainActivity.

#### 4.2 Update MainActivity
**File:** `android/app/src/main/AndroidManifest.xml`  
**Status:** NEEDS IMPLEMENTATION

Add notification permission (API 33+):
```xml
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

Add to `android/app/src/main/java/com/aetheria/app/MainActivity.java`:
```java
import com.aetheria.app.NotificationChannels;

public class MainActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // Create notification channels
        NotificationChannels.createNotificationChannels(this);
        
        // ... rest of initialization
    }
}
```

#### 4.3 Request Notification Permission (Runtime)
**File:** `android/app/src/main/java/com/aetheria/app/MainActivity.java`  
**Status:** NEEDS IMPLEMENTATION

```java
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

public class MainActivity extends AppCompatActivity {
    private static final int PERMISSION_REQUEST_CODE = 101;
    
    private void requestNotificationPermission() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(
                this,
                android.Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
                
                ActivityCompat.requestPermissions(
                    this,
                    new String[]{android.Manifest.permission.POST_NOTIFICATIONS},
                    PERMISSION_REQUEST_CODE
                );
            }
        }
    }
    
    @Override
    public void onRequestPermissionsResult(int requestCode, 
            String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        
        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (grantResults.length > 0 
                && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                Log.d("Aetheria", "Notification permission granted");
            }
        }
    }
}
```

---

### ✅ PHASE 5: ENVIRONMENT SETUP (CRITICAL)

#### 5.1 Create .env File for Local Development

```
# Database
POSTGRES_DB=aetheria
POSTGRES_USER=postgres
POSTGRES_PASSWORD=dev_password_here
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Django
DEBUG=True
SECRET_KEY=your-secret-key-here-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

# Firebase
FIREBASE_CREDENTIALS_JSON={...json from firebase-service-account.json...}

# Redis
REDIS_URL=redis://localhost:6379/0

# Cloudinary (Optional)
CLOUDINARY_URL=cloudinary://...

# Email (for password reset)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Sentry (Optional, for error tracking)
SENTRY_DSN=

# Environment
ENVIRONMENT=development
```

#### 5.2 Create .env for Production (Vercel/Deployment)

Set these in your deployment platform's environment variables:
```
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@host:5432/aetheria
REDIS_URL=redis://...
FIREBASE_CREDENTIALS_JSON={...}
ENVIRONMENT=production
```

---

## VERIFICATION CHECKLIST

### Local Development Testing

- [ ] PostgreSQL database connects and migrations run
- [ ] WebSocket connects and shows "connected" status
- [ ] Notification toast appears when message received
- [ ] Device token registers successfully
- [ ] Logging writes to `logs/aetheria.log`
- [ ] Firebase console shows device tokens
- [ ] Android app requests notification permission
- [ ] Android notification channels visible in Settings

### Pre-Production Testing

- [ ] Run load test: `python manage.py shell`
  ```python
  from django.test.utils import override_settings
  from django.test import Client
  import concurrent.futures
  
  client = Client()
  with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
      futures = [executor.submit(client.get, '/') for _ in range(100)]
      concurrent.futures.wait(futures)
  ```

- [ ] Check database indexes exist:
  ```sql
  SELECT indexname FROM pg_indexes WHERE tablename='users_message';
  ```

- [ ] Verify Redis connection:
  ```python
  from django_redis import get_redis_connection
  redis = get_redis_connection('default')
  redis.ping()  # Should return True
  ```

- [ ] Test Firebase push notifications manually
- [ ] Test WebSocket reconnection by killing connection
- [ ] Verify HTTPS/WSS works on production domain

---

## DEPLOYMENT STEPS

### 1. Prepare Environment

```bash
# Create production database
createdb -U postgres aetheria_prod

# Set environment variables on deployment platform
# (See .env production section above)

# Run migrations
python manage.py migrate --database=default

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Create indexes
python manage.py shell < create_indexes.sql

# Create notification channels (Android)
# (Already done in NotificationChannels.java)
```

### 2. Deploy Code

For Vercel:
```bash
git add .
git commit -m "Production fixes: PostgreSQL, logging, WebSocket, Firebase"
git push  # Triggers Vercel deployment
```

### 3. Post-Deployment Verification

```bash
# Check logs
tail -f logs/aetheria.log

# Monitor WebSocket connections
tail -f logs/websocket.log

# Check Firebase push deliveries
tail -f logs/firebase.log

# Test from browser console
console.log(window.AetheriaWebSockets.chat.getStatus())

# Should return:
# {
#   isConnected: true,
#   isConnecting: false,
#   reconnectAttempts: 0,
#   queuedMessages: 0
# }
```

### 4. Configure Uptime Monitoring

Add health check endpoint:
```python
# In socialmedia/urls.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def health_check(request):
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat()
    })

path('health/', health_check, name='health_check'),
```

Monitor with: Uptime Robot, Datadog, etc.

---

## TESTING COMMANDS

```bash
# Run unit tests
python manage.py test

# Run WebSocket tests
python manage.py test users.tests.ChatConsumerTest

# Check for N+1 queries
python manage.py runserver --wsgi-handler=django_extensions.wsgi.DjangoHandler

# Load test
locust -f locustfile.py

# Security check
python manage.py check --deploy

# Performance profiling
pip install django-debug-toolbar
# Set DEBUG_TOOLBAR = True in settings (dev only)
```

---

## ROLLBACK PROCEDURE

If critical issues occur:

```bash
# Rollback database migration
python manage.py migrate users 0XXX  # Use previous migration number

# Revert code
git revert HEAD

# Restore from backup
psql aetheria < backup.sql

# Clear Redis cache
redis-cli FLUSHDB
```

---

## MONITORING & ALERTS

### Set Up Alerts For:

1. **Database Connection Errors**
   - Configure in logging to email admin

2. **Firebase Push Failures**
   - Check firebase.log for "Firebase push failed"

3. **WebSocket Disconnections**
   - Monitor websocket.log for connection issues

4. **High Error Rates**
   - Alert if ERROR rate > 5 per minute

5. **Disk Space**
   - Monitor logs directory size

### Dashboard

Set up Grafana dashboard with:
- WebSocket connection count
- Firebase push success rate
- Database query time
- API response time
- Error rate

---

## NEXT STEPS AFTER LAUNCH

### Week 1:
- [ ] Monitor logs for errors
- [ ] Fix any runtime issues
- [ ] Gather user feedback

### Week 2:
- [ ] Implement notification grouping
- [ ] Add notification sounds
- [ ] Optimize N+1 queries

### Week 3:
- [ ] Implement video/voice messages
- [ ] Add search refinement
- [ ] Optimize media loading

### Month 2:
- [ ] Full load testing (1000+ concurrent users)
- [ ] Security penetration testing
- [ ] Performance optimization

---

## SUPPORT & TROUBLESHOOTING

### Common Issues:

**WebSocket won't connect:**
- Check ASGI_APPLICATION in settings
- Verify Daphne is running: `ps aux | grep daphne`
- Check firewall allows WebSocket (port 443 for WSS)

**Notifications not arriving:**
- Check device token in database: `SELECT * FROM users_devicetoken;`
- Verify Firebase service account file path
- Check firebase.log for errors

**Database too slow:**
- Run index creation script
- Check for missing indexes: `EXPLAIN ANALYZE`
- Consider query optimization or caching

**Memory leak:**
- Check for unclosed WebSocket connections
- Monitor Redis memory usage
- Check for circular imports

---

**Last Updated:** June 9, 2026  
**Status:** CRITICAL - IMPLEMENTATION IN PROGRESS

