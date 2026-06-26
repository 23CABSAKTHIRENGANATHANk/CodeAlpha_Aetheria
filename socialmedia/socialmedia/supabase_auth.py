"""
Supabase Auth helpers for Aetheria.
====================================
Provides server-side wrappers around the Supabase Auth API so Django views
can sync user lifecycle events (register, login, logout, password reset)
with Supabase without exposing the service-role key to the browser.

All functions return a dict on success or None on failure.
Exceptions are caught and logged — callers should handle None gracefully.
"""

import logging
import os
from typing import Optional

import jwt

# supabase_client.py lives at the project root (socialmedia/supabase_client.py),
# not inside the socialmedia Django app package, so import it as top-level.
try:
    from supabase_client import get_supabase_client
except ImportError:
    # Fallback for environments where it may be installed as part of the app package
    try:
        from socialmedia.supabase_client import get_supabase_client
    except ImportError:
        def get_supabase_client():
            return None

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Token verification
# ──────────────────────────────────────────────────────────────

def get_user_info_from_token(token: str) -> Optional[dict]:
    """Return a dict with user information extracted from a Supabase JWT.

    Tries the Supabase Admin API first, then falls back to local JWT decode
    using SUPABASE_JWT_SECRET (avoids a network round-trip in hot paths).
    """
    if not token:
        return None

    client = get_supabase_client()

    # 1. Try Supabase Admin API (authoritative, validates revocation)
    if client:
        try:
            user_resp = client.auth.get_user(token)
            if user_resp and getattr(user_resp, "user", None):
                user = user_resp.user
                user_dict = user if isinstance(user, dict) else vars(user)
                return {
                    "id": user_dict.get("id"),
                    "email": user_dict.get("email"),
                    "phone": user_dict.get("phone"),
                    "role": user_dict.get("role"),
                    "email_confirmed": bool(user_dict.get("email_confirmed_at")),
                    "raw": user_dict,
                }
        except Exception as exc:
            logger.debug("Supabase Admin API token check failed: %s", exc)

    # 2. Fallback: local JWT decode (no network, but cannot detect revocation)
    secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not secret:
        return None
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})
        return {
            "id": payload.get("sub") or payload.get("user_id") or payload.get("id"),
            "email": payload.get("email"),
            "email_confirmed": True,  # If JWT exists and valid, assume confirmed
            "raw": payload,
        }
    except jwt.ExpiredSignatureError:
        logger.debug("Supabase JWT expired")
    except Exception as exc:
        logger.debug("Supabase JWT decode failed: %s", exc)

    return None


# ──────────────────────────────────────────────────────────────
# User lifecycle (server-side — uses service-role key)
# ──────────────────────────────────────────────────────────────

def sign_up_user(email: str, password: str, metadata: Optional[dict] = None) -> Optional[dict]:
    """Create a new user in Supabase Auth.

    Args:
        email: User's email address.
        password: Plain-text password (Supabase hashes it).
        metadata: Optional dict stored in Supabase auth.users.raw_user_meta_data.

    Returns:
        dict with keys: id, email, email_confirmed — or None on failure.
    """
    client = get_supabase_client()
    if not client:
        logger.warning("sign_up_user: Supabase client not configured — skipping Supabase sync.")
        return None
    try:
        payload = {"email": email, "password": password}
        if metadata:
            payload["options"] = {"data": metadata}
        response = client.auth.sign_up(payload)
        user = getattr(response, "user", None)
        if not user:
            logger.warning("sign_up_user: No user in response — %s", response)
            return None
        user_dict = user if isinstance(user, dict) else vars(user)
        logger.info("Supabase sign-up OK for %s (id=%s)", email, user_dict.get("id"))
        return {
            "id": user_dict.get("id"),
            "email": user_dict.get("email"),
            "email_confirmed": bool(user_dict.get("email_confirmed_at")),
        }
    except Exception as exc:
        logger.error("sign_up_user failed for %s: %s", email, exc)
        return None


def sign_in_user(email: str, password: str) -> Optional[dict]:
    """Sign in a user and return Supabase session tokens.

    Returns:
        dict with keys: access_token, refresh_token, user_id, email — or None on failure.
    """
    client = get_supabase_client()
    if not client:
        return None
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        session = getattr(response, "session", None)
        user = getattr(response, "user", None)
        if not session or not user:
            return None
        session_dict = session if isinstance(session, dict) else vars(session)
        user_dict = user if isinstance(user, dict) else vars(user)
        return {
            "access_token": session_dict.get("access_token"),
            "refresh_token": session_dict.get("refresh_token"),
            "expires_in": session_dict.get("expires_in"),
            "user_id": user_dict.get("id"),
            "email": user_dict.get("email"),
        }
    except Exception as exc:
        logger.error("sign_in_user failed for %s: %s", email, exc)
        return None


def sign_out_user(access_token: str) -> bool:
    """Invalidate a Supabase session (server-side sign-out).

    Returns True if sign-out succeeded (or was unnecessary), False on error.
    """
    client = get_supabase_client()
    if not client or not access_token:
        return True  # No-op is acceptable
    try:
        client.auth.sign_out()
        return True
    except Exception as exc:
        logger.warning("sign_out_user failed: %s", exc)
        return False


def send_password_reset_email(email: str, redirect_url: Optional[str] = None) -> bool:
    """Trigger a Supabase Auth password reset email.

    Args:
        email: User's email address.
        redirect_url: URL Supabase redirects to after the user clicks the link.

    Returns:
        True if the email was sent, False on error.
    """
    client = get_supabase_client()
    if not client:
        logger.warning("send_password_reset_email: Supabase not configured.")
        return False
    try:
        options = {}
        if redirect_url:
            options["redirect_to"] = redirect_url
        client.auth.reset_password_email(email, options=options or None)
        logger.info("Supabase password reset email sent to %s", email)
        return True
    except Exception as exc:
        logger.error("send_password_reset_email failed for %s: %s", email, exc)
        return False


def update_user_password(access_token: str, new_password: str) -> bool:
    """Update user's password in Supabase Auth using their access token.

    Returns True on success, False on failure.
    """
    client = get_supabase_client()
    if not client or not access_token:
        return False
    try:
        # Authenticate the client with the user's token for this operation
        authed_client = get_supabase_client()
        authed_client.auth.set_session(access_token, "")
        authed_client.auth.update_user({"password": new_password})
        logger.info("Supabase password updated for access_token=...%s", access_token[-8:])
        return True
    except Exception as exc:
        logger.error("update_user_password failed: %s", exc)
        return False


def update_user_email(access_token: str, new_email: str) -> bool:
    """Update user's email in Supabase Auth using their access token.

    Returns True on success, False on failure.
    """
    client = get_supabase_client()
    if not client or not access_token:
        return False
    try:
        authed_client = get_supabase_client()
        authed_client.auth.set_session(access_token, "")
        authed_client.auth.update_user({"email": new_email})
        logger.info("Supabase email update requested for new_email=%s", new_email)
        return True
    except Exception as exc:
        logger.error("update_user_email failed: %s", exc)
        return False


def get_supabase_user_by_id(supabase_uid: str) -> Optional[dict]:
    """Fetch a Supabase Auth user by their UUID (admin API).

    Returns dict with user info or None.
    """
    client = get_supabase_client()
    if not client or not supabase_uid:
        return None
    try:
        response = client.auth.admin.get_user_by_id(supabase_uid)
        user = getattr(response, "user", None)
        if not user:
            return None
        user_dict = user if isinstance(user, dict) else vars(user)
        return {
            "id": user_dict.get("id"),
            "email": user_dict.get("email"),
            "email_confirmed": bool(user_dict.get("email_confirmed_at")),
            "created_at": user_dict.get("created_at"),
        }
    except Exception as exc:
        logger.error("get_supabase_user_by_id failed for %s: %s", supabase_uid, exc)
        return None
