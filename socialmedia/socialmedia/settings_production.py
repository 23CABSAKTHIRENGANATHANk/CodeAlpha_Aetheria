"""
Production settings for Aetheria Social Media Platform
Overrides default settings with security-hardened configuration
"""

import os
from .settings import *

# ============================================================
# SECURITY CONFIGURATION - PRODUCTION HARDENED
# ============================================================

# Generate a strong SECRET_KEY for production
# NEVER use django-insecure prefix in production
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-x4n5uj&qkfkw-=&_n0lx6u-yz1a8f_^$mhaz($vn5-55$9st4s"
)

# Validate SECRET_KEY in production
if SECRET_KEY.startswith("django-insecure-"):
    raise RuntimeError(
        "⚠️ SECURITY ERROR: Using django-insecure key in production!"
        "\n Set SECRET_KEY environment variable to a secure random string."
        "\n Generate with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
    )

# DEBUG must be False in production
DEBUG = False
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

if "*" in ALLOWED_HOSTS:
    raise RuntimeError("⚠️ SECURITY ERROR: ALLOWED_HOSTS contains wildcard '*' in production!")

# ============================================================
# SSL/HTTPS SECURITY
# ============================================================

SECURE_SSL_REDIRECT = True  # Redirect all HTTP to HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # For proxies/load balancers
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ============================================================
# COOKIE SECURITY
# ============================================================

SESSION_COOKIE_SECURE = True  # Only send over HTTPS
SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SECURE = True  # Only send over HTTPS
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if os.environ.get("CSRF_TRUSTED_ORIGINS") else []

# ============================================================
# SECURITY HEADERS
# ============================================================

SECURE_CONTENT_SECURITY_POLICY = {
    "default-src": ["'self'"],
    "script-src": ["'self'", "cdn.jsdelivr.net", "cdnjs.cloudflare.com"],
    "style-src": ["'self'", "'unsafe-inline'", "cdnjs.cloudflare.com"],
    "img-src": ["'self'", "data:", "https://"],
    "font-src": ["'self'", "cdnjs.cloudflare.com"],
    "connect-src": ["'self'", "ws:", "wss:"],
    "media-src": ["'self'"],
    "object-src": ["'none'"],
    "upgrade-insecure-requests": [],
}

SECURE_CONTENT_SECURITY_POLICY_REPORT_ONLY = False

# Additional security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# ============================================================
# DATABASE - PRODUCTION OPTIMIZED
# ============================================================

# Use environment-based database configuration
if os.environ.get("DATABASE_URL"):
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 600,
        "OPTIONS": {
            "connect_timeout": 10,
            "sslmode": "require",  # Force SSL connection
        },
        "ATOMIC_REQUESTS": True,  # Wrap each request in transaction
        "AUTOCOMMIT": False,
        "BACKUP_COUNT": 5,
    }

# Disable SQLite in production
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3" and not DEBUG:
    raise RuntimeError("⚠️ SECURITY ERROR: SQLite not allowed in production!")

# ============================================================
# CACHING - PRODUCTION OPTIMIZED
# ============================================================

if os.environ.get("REDIS_URL"):
    CACHES["default"]["OPTIONS"]["CONNECTION_POOL_KWARGS"]["max_connections"] = 100
    CACHES["default"]["OPTIONS"]["SOCKET_CONNECT_TIMEOUT"] = 2
    CACHES["default"]["TIMEOUT"] = 3600  # 1 hour

# ============================================================
# LOGGING - PRODUCTION COMPREHENSIVE
# ============================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR.parent, 'logs', 'aetheria.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR.parent, 'logs', 'errors.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file', 'error_file'],
    },
    'loggers': {
        'django': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False,
        },
        'django.security': {
            'level': 'WARNING',
            'handlers': ['console', 'error_file'],
            'propagate': False,
        },
        'django.request': {
            'level': 'WARNING',
            'handlers': ['console', 'error_file'],
            'propagate': False,
        },
    }
}

# Create logs directory if it doesn't exist
os.makedirs(os.path.join(BASE_DIR.parent, 'logs'), exist_ok=True)

# ============================================================
# STATIC FILES & MEDIA - CDN OPTIMIZED
# ============================================================

# Use Cloudinary for media files in production
if os.environ.get("CLOUDINARY_URL"):
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    MEDIA_URL = '/media/'
else:
    # Fallback to local storage
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR.parent, 'media')

# Static files optimization
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR.parent, 'staticfiles')

# ============================================================
# ALLOWED FILE UPLOADS
# ============================================================

FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB

ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

# ============================================================
# SESSION MANAGEMENT
# ============================================================

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 1209600  # 2 weeks

# ============================================================
# EMAIL CONFIGURATION
# ============================================================

if os.environ.get("EMAIL_BACKEND") == "sendgrid":
    EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@aetheria.local")

# ============================================================
# API RATE LIMITING
# ============================================================

RATE_LIMIT_ENABLED = True
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_PERIOD = 3600  # 1 hour

# ============================================================
# CORS CONFIGURATION
# ============================================================

CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if os.environ.get("CORS_ALLOWED_ORIGINS") else []
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']

# ============================================================
# FIREBASE CONFIGURATION
# ============================================================

FIREBASE_CREDENTIALS_PATH = os.environ.get("FIREBASE_CREDENTIALS_PATH")

# ============================================================
# MONITORING & PERFORMANCE
# ============================================================

# Enable query logging for optimization
if os.environ.get("DEBUG_TOOLBAR"):
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1']

# Sentry error tracking (optional)
SENTRY_DSN = os.environ.get("SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=0.1,
            send_default_pii=False,
            environment=os.environ.get("ENVIRONMENT", "production")
        )
    except ImportError:
        pass

# ============================================================
# HEALTH CHECK ENDPOINT
# ============================================================

HEALTH_CHECK_TOKEN = os.environ.get("HEALTH_CHECK_TOKEN", "default-token-change-me")

print("✅ Production settings loaded successfully")
print(f"   DEBUG: {DEBUG}")
print(f"   SECRET_KEY: {'***' if SECRET_KEY else 'NOT SET'}")
print(f"   ALLOWED_HOSTS: {ALLOWED_HOSTS}")
print(f"   Database: {'PostgreSQL' if 'postgresql' in DATABASES['default']['ENGINE'] else 'SQLite'}")
print(f"   Redis: {'Enabled' if os.environ.get('REDIS_URL') else 'Disabled'}")
print(f"   SSL/HTTPS: {'Enabled' if SECURE_SSL_REDIRECT else 'Disabled'}")
