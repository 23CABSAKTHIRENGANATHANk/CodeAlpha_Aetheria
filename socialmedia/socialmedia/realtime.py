"""Minimal helpers for Supabase realtime usage.

Notes:
- In many apps realtime subscriptions are implemented in the frontend using
  Supabase JS (`@supabase/supabase-js`). This module provides a minimal
  server-side helper to expose the `realtime` client if needed.

Usage (recommended): Use Supabase JS in browser/mobile clients to subscribe
to changes directly. For server-side listeners, see Supabase docs for
`realtime` server subscriptions or forward events to Django Channels.
"""
from .supabase_client import get_supabase_client


def get_realtime():
    client = get_supabase_client()
    if not client:
        return None
    # The supabase client exposes realtime features depending on SDK version
    return getattr(client, 'realtime', None)


__all__ = ['get_realtime']
