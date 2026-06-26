from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse


class EmailVerificationMiddleware:
    """Block unverified users from accessing the app.

    Verification is considered complete if EITHER:
      - Django's UserSettings.email_verified is True (set via our OTP flow), OR
      - The Supabase Auth record for this user has email_confirmed_at set
        (set when the user clicks the Supabase confirmation email).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path
            # Always allow access to admin, static, and media paths
            if path.startswith('/admin/') or path.startswith('/static/') or path.startswith('/media/'):
                return self.get_response(request)

            verified = self._is_verified(request)

            if not verified:
                allowed_names = ['verify_email', 'logout', 'landing']
                allowed_paths = []
                for name in allowed_names:
                    try:
                        allowed_paths.append(reverse(name))
                    except Exception:
                        pass

                if not any(path.startswith(p) for p in allowed_paths):
                    return redirect('verify_email')

        return self.get_response(request)

    @staticmethod
    def _is_verified(request) -> bool:
        """Return True if the user's email is verified by either Django or Supabase."""
        # 1. Django OTP verification (primary)
        try:
            if request.user.settings.email_verified:
                return True
        except Exception:
            return True  # Fallback: allow if settings model not accessible

        # 2. Supabase Auth verification (secondary — check cached Supabase uid)
        try:
            from django.conf import settings as django_settings
            if not getattr(django_settings, 'SUPABASE_URL', ''):
                return False  # Supabase not configured → rely on Django only

            supabase_uid = getattr(request.user, 'settings', None) and request.user.settings.supabase_uid
            if not supabase_uid:
                return False

            # Cache the Supabase email_confirmed status in the session to avoid
            # repeated API calls on every request.
            session_key = f'supabase_email_confirmed_{supabase_uid}'
            if request.session.get(session_key):
                return True

            from socialmedia.supabase_auth import get_supabase_user_by_id
            sb_user = get_supabase_user_by_id(supabase_uid)
            if sb_user and sb_user.get('email_confirmed'):
                # Sync back to Django UserSettings to avoid future API calls
                try:
                    request.user.settings.email_verified = True
                    request.user.settings.save(update_fields=['email_verified'])
                except Exception:
                    pass
                request.session[session_key] = True
                return True
        except Exception:
            pass

        return False


import time
from django.core.cache import cache


class APIRateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith('/api/') or path.startswith('/login/') or path.startswith('/register/'):
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
            route_base = path.split('/')[1] if len(path.split('/')) > 1 else 'route'
            key = f"rate_limit_{ip}_{route_base}"

            requests = cache.get(key, [])
            now = time.time()
            requests = [r for r in requests if now - r < 60]

            if len(requests) >= 60:
                return JsonResponse({'error': 'Too many requests. Please slow down.'}, status=429)

            requests.append(now)
            cache.set(key, requests, 60)

        return self.get_response(request)
