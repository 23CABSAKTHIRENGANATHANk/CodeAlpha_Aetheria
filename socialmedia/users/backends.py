from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from socialmedia.supabase_auth import get_user_info_from_token


class SupabaseAuthBackend(BaseBackend):
    """Authenticate users using a Supabase-issued JWT (Bearer token).

    The backend expects `authenticate(request, token=...)` to be called.
    It will get user information from Supabase and create or update a
    corresponding Django `User` object.
    """

    def authenticate(self, request, token=None, **kwargs):
        if not token:
            return None

        info = get_user_info_from_token(token)
        if not info:
            return None

        email = info.get('email')
        uid = info.get('id') or (email and email.split('@')[0])
        if not email and not uid:
            return None

        username = uid if uid else (email.split('@')[0] if email else 'user')

        user, created = User.objects.get_or_create(username=username, defaults={'email': email or ''})
        # Update email if changed
        if email and user.email != email:
            user.email = email
            user.save()

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
