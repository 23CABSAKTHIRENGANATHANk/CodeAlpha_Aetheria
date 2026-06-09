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
        # Try to get from environment first
        if os.environ.get('FIREBASE_CREDENTIALS_JSON'):
            firebase_creds = json.loads(os.environ.get('FIREBASE_CREDENTIALS_JSON'))
            context['firebase_api_key'] = firebase_creds.get('apiKey', '')
            context['firebase_auth_domain'] = firebase_creds.get('authDomain', '')
            context['firebase_project_id'] = firebase_creds.get('projectId', '')
            context['firebase_storage_bucket'] = firebase_creds.get('storageBucket', '')
            context['firebase_messaging_sender_id'] = firebase_creds.get('messagingSenderId', '')
            context['firebase_app_id'] = firebase_creds.get('appId', '')
    except Exception as e:
        # If Firebase config fails, provide empty strings (notifications optional)
        context['firebase_api_key'] = ''
        context['firebase_auth_domain'] = ''
        context['firebase_project_id'] = ''
        context['firebase_storage_bucket'] = ''
        context['firebase_messaging_sender_id'] = ''
        context['firebase_app_id'] = ''
    
    # Security headers for frontend
    context['csrf_token'] = request.META.get('CSRF_COOKIE', '')
    context['web_app_name'] = 'Aetheria'
    
    return context
