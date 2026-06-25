"""
Minimal, self-contained test settings.
This avoids importing the full `settings.py` which enforces production guards
and can raise during test-time configuration.
"""
import os
from pathlib import Path

# Basic paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-test-key")
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Minimal installed apps for tests
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users.apps.UsersConfig",
    "posts.apps.PostsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # Include app middleware used by tests
    "users.middleware.EmailVerificationMiddleware",
    "users.middleware.APIRateLimitMiddleware",
]

# Use a minimal URL conf to avoid importing app-level view modules at import time
ROOT_URLCONF = "socialmedia.test_urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = None
ASGI_APPLICATION = None

# Use in-memory SQLite for tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Static/media
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "django.core.files.storage.StaticFilesStorage"

# Session / CSRF
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Testing helper flag
AETHERIA_TEST_FRIENDLY = True
