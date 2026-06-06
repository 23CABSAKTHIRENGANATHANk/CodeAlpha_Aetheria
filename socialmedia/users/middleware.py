from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse

class EmailVerificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Bypass check for admin/static/media
            path = request.path
            if path.startswith('/admin/') or path.startswith('/static/') or path.startswith('/media/'):
                return self.get_response(request)

            try:
                verified = request.user.settings.email_verified
            except Exception:
                verified = True # Fallback

            if not verified:
                # Allowed URLs while unverified
                allowed_names = ['verify_email', 'logout', 'landing']
                allowed_paths = []
                for name in allowed_names:
                    try:
                        allowed_paths.append(reverse(name))
                    except Exception:
                        pass
                
                # If the path is not allowed, redirect to verify-email
                if not any(path.startswith(p) for p in allowed_paths):
                    return redirect('verify_email')

        return self.get_response(request)


import time
from django.core.cache import cache

class APIRateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith('/api/') or path.startswith('/login/') or path.startswith('/register/'):
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
            # Throttling key per IP & route base
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

