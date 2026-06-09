from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
import os
import json


def global_sidebar_context(request):
    """
    Injects trending_hashtags, Firebase config, and security context into every template.
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
    
    # Firebase Configuration (for notifications)
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
    except Exception as e:
        context['firebase_api_key'] = ''
        context['firebase_auth_domain'] = ''
        context['firebase_project_id'] = ''
        context['firebase_storage_bucket'] = ''
        context['firebase_messaging_sender_id'] = ''
        context['firebase_app_id'] = ''
        context['firebase_vapid_key'] = 'REPLACE_WITH_VAPID_KEY'
    
    # Security headers for frontend
    context['csrf_token'] = request.META.get('CSRF_COOKIE', '')
    context['web_app_name'] = 'Aetheria'
    
    return context
