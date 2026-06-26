from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import authenticate


class SupabaseAuthMiddleware(MiddlewareMixin):
    """Middleware that reads `Authorization: Bearer <token>` and authenticates via Supabase.

    If authentication succeeds, `request.user` is set to the corresponding Django user.
    """

    def process_request(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION') or request.headers.get('Authorization')
        if not auth:
            return None

        if auth.startswith('Bearer '):
            token = auth.split(' ', 1)[1].strip()
            user = authenticate(request, token=token)
            if user:
                request.user = user

        return None
