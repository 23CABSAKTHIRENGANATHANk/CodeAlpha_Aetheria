"""
Supabase Authentication Backend for Django.
=============================================
Handles two authentication modes:

1. Bearer JWT (API clients):
   authenticate(request, token="<supabase_jwt>")
   → Validates the JWT via Supabase Admin API or local secret decode
   → Gets-or-creates the matching Django User

2. Email + password (web login synced with Supabase):
   authenticate(request, username="...", password="...", use_supabase=True)
   → Signs in via Supabase to obtain session tokens
   → Gets-or-creates the matching Django User
   → Stores supabase_uid on UserSettings for future lookups

This backend always falls through to ModelBackend for standard Django auth.
"""

import logging

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User

from socialmedia.supabase_auth import get_user_info_from_token, sign_in_user

logger = logging.getLogger(__name__)


class SupabaseAuthBackend(BaseBackend):
    """Authenticate users using Supabase JWT tokens or email+password via Supabase."""

    # ── JWT authentication (for API clients sending Bearer tokens) ──────────

    def authenticate(self, request, token=None, username=None, password=None, use_supabase=False, **kwargs):
        # Mode 1: JWT Bearer token
        if token:
            return self._authenticate_jwt(token)

        # Mode 2: Email+password via Supabase (opt-in with use_supabase=True)
        if use_supabase and username and password:
            return self._authenticate_password(username, password, request)

        return None

    def _authenticate_jwt(self, token: str) -> "User | None":
        """Validate a Supabase JWT and return the matching Django User."""
        info = get_user_info_from_token(token)
        if not info:
            return None

        email = info.get("email")
        uid = info.get("id")

        if not email and not uid:
            logger.warning("SupabaseAuthBackend: token has neither email nor id")
            return None

        # Derive a stable username from the Supabase UUID
        username = uid if uid else (email.split("@")[0] if email else "user")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email or ""},
        )

        if created:
            logger.info("SupabaseAuthBackend: created Django User for Supabase id=%s email=%s", uid, email)
        elif email and user.email != email:
            user.email = email
            user.save(update_fields=["email"])

        # Sync supabase_uid into UserSettings
        if uid:
            self._sync_supabase_uid(user, uid)

        return user

    def _authenticate_password(self, email_or_username: str, password: str, request) -> "User | None":
        """Sign in via Supabase email+password and sync Django user."""
        # Resolve email: username might be passed or the actual email
        email = email_or_username
        if "@" not in email_or_username:
            try:
                user = User.objects.get(username=email_or_username)
                email = user.email
            except User.DoesNotExist:
                return None

        session = sign_in_user(email, password)
        if not session:
            return None

        # Store tokens in session if available
        if request and hasattr(request, "session") and session.get("access_token"):
            request.session["supabase_access_token"] = session["access_token"]
            request.session["supabase_refresh_token"] = session.get("refresh_token", "")

        # Get or create Django User from the Supabase session
        uid = session.get("user_id")
        username = uid if uid else email.split("@")[0]

        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": username},
        )
        if created:
            logger.info("SupabaseAuthBackend: created Django User from Supabase sign-in email=%s", email)

        if uid:
            self._sync_supabase_uid(user, uid)

        return user

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _sync_supabase_uid(user: "User", uid: str) -> None:
        """Store Supabase UUID on UserSettings (non-fatal if model not ready)."""
        try:
            from users.models import UserSettings
            settings_obj, _ = UserSettings.objects.get_or_create(user=user)
            if settings_obj.supabase_uid != uid:
                settings_obj.supabase_uid = uid
                settings_obj.save(update_fields=["supabase_uid"])
        except Exception as exc:
            logger.debug("_sync_supabase_uid failed: %s", exc)

    def get_user(self, user_id: int) -> "User | None":
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
