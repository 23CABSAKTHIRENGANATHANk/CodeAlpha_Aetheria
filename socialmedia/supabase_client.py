import os
from supabase import create_client


def get_supabase_client():
    """Return a ready-to-use Supabase client or None if not configured."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)


__all__ = ["get_supabase_client"]
