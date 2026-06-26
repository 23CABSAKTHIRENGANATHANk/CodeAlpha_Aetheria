import os
import jwt
from typing import Optional
from .supabase_client import get_supabase_client


def get_user_info_from_token(token: str) -> Optional[dict]:
    """Return a dict with user information extracted from Supabase token.

    Tries Supabase client first, then falls back to JWT decode using
    SUPABASE_JWT_SECRET environment variable.
    """
    if not token:
        return None

    client = get_supabase_client()
    # Try Supabase client method if available
    try:
        if client:
            # supabase-py can decode/verify token or fetch user via admin endpoints
            try:
                user_resp = client.auth.get_user(token)
                # The SDK may return a dict-like object
                if user_resp and getattr(user_resp, 'user', None):
                    user = user_resp.user if hasattr(user_resp, 'user') else user_resp.get('user')
                    return {
                        'id': user.get('id'),
                        'email': user.get('email'),
                        'phone': user.get('phone'),
                        'role': user.get('role'),
                        'raw': user,
                    }
            except Exception:
                # Fall through to JWT decode
                pass

    except Exception:
        pass

    # Fallback: decode JWT with SUPABASE_JWT_SECRET
    secret = os.environ.get('SUPABASE_JWT_SECRET')
    if not secret:
        return None

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})
        return {
            'id': payload.get('sub') or payload.get('user_id') or payload.get('id'),
            'email': payload.get('email'),
            'raw': payload,
        }
    except Exception:
        return None
