from django.db.models import Count
from django.utils import timezone
from datetime import timedelta


def global_sidebar_context(request):
    """
    Injects trending_hashtags into every template context for authenticated users.
    Queries hashtags with the most posts in the last 7 days.
    """
    if not request.user.is_authenticated:
        return {}

    try:
        from posts.models import Hashtag
        trending = Hashtag.objects.filter(
            posts__created_at__gte=timezone.now() - timedelta(days=7)
        ).annotate(
            post_count=Count('posts', distinct=True)
        ).order_by('-post_count')[:6]
        return {'trending_hashtags': list(trending)}
    except Exception:
        return {'trending_hashtags': []}
