from django.db.models import Count
from django.utils import timezone
from django.middleware.csrf import get_token
from datetime import timedelta
import os
import json


def global_sidebar_context(request):
    """
    Injects trending_hashtags, Firebase config, Supabase config,
    and security context into every template.

    NOTE: Only the ANON KEY is exposed to templates (safe for client-side use).
          The SERVICE-ROLE KEY (SUPABASE_KEY) is never passed to templates.
    """
    context = {}

    if request.user.is_authenticated:
        try:
            from posts.models import Hashtag
            trending = Hashtag.objects.filter(
                posts__created_at__gte=timezone.now() - timedelta(days=7)
            ).annotate(
                post_count=Count('posts', distinct=True)
            ).order_by('-post_count')[:6]
            context['trending_hashtags'] = list(trending)
        except Exception:
            context['trending_hashtags'] = []

    # Firebase Configuration (for push notifications)
    try:
        context['firebase_api_key'] = os.environ.get('FIREBASE_API_KEY', '')
        context['firebase_auth_domain'] = os.environ.get('FIREBASE_AUTH_DOMAIN', '')
        context['firebase_project_id'] = os.environ.get('FIREBASE_PROJECT_ID', '')
        context['firebase_storage_bucket'] = os.environ.get('FIREBASE_STORAGE_BUCKET', '')
        context['firebase_messaging_sender_id'] = os.environ.get('FIREBASE_MESSAGING_SENDER_ID', '')
        context['firebase_app_id'] = os.environ.get('FIREBASE_APP_ID', '')
        context['firebase_vapid_key'] = os.environ.get('FIREBASE_VAPID_KEY', 'REPLACE_WITH_VAPID_KEY')

        # Fallback to FIREBASE_CREDENTIALS_JSON if not defined directly
        if not context['firebase_api_key'] and os.environ.get('FIREBASE_CREDENTIALS_JSON'):
            firebase_creds = json.loads(os.environ.get('FIREBASE_CREDENTIALS_JSON'))
            context['firebase_api_key'] = firebase_creds.get('apiKey', '')
            context['firebase_auth_domain'] = firebase_creds.get('authDomain', '')
            context['firebase_project_id'] = firebase_creds.get('projectId', '')
            context['firebase_storage_bucket'] = firebase_creds.get('storageBucket', '')
            context['firebase_messaging_sender_id'] = firebase_creds.get('messagingSenderId', '')
            context['firebase_app_id'] = firebase_creds.get('appId', '')
            context['firebase_vapid_key'] = firebase_creds.get('vapidKey', 'REPLACE_WITH_VAPID_KEY')
    except Exception:
        context['firebase_api_key'] = ''
        context['firebase_auth_domain'] = ''
        context['firebase_project_id'] = ''
        context['firebase_storage_bucket'] = ''
        context['firebase_messaging_sender_id'] = ''
        context['firebase_app_id'] = ''
        context['firebase_vapid_key'] = 'REPLACE_WITH_VAPID_KEY'

    # ── Supabase client configuration (anon key only — safe for JS) ──────────
    # SUPABASE_ANON_KEY is the public key for client-side Supabase JS SDK.
    # The service-role SUPABASE_KEY is NEVER exposed to templates.
    from django.conf import settings as django_settings
    context['supabase_url'] = getattr(django_settings, 'SUPABASE_URL', '') or os.environ.get('SUPABASE_URL', '')
    context['supabase_anon_key'] = getattr(django_settings, 'SUPABASE_ANON_KEY', '') or os.environ.get('SUPABASE_ANON_KEY', '')
    # Current user ID for Realtime channel filtering (authenticated users only)
    context['current_user_id'] = request.user.id if request.user.is_authenticated else None
    # ─────────────────────────────────────────────────────────────────────────

    # Security headers for frontend
    context['csrf_token'] = get_token(request)
    context['web_app_name'] = 'Aetheria'

    return context
