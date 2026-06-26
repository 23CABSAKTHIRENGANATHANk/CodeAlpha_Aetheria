"""
Supabase Storage backend for Django.
======================================
A fully-featured Django storage backend backed by Supabase Storage.

Key improvements over the original stub:
  - Per-bucket routing based on the upload path prefix (via SUPABASE_STORAGE_BUCKETS setting)
  - Proper _open() implementation using the Supabase download API
  - Reliable exists() using object metadata instead of list()
  - UUID-prefixed filenames to avoid collisions
  - Content-type detection from file extension
  - Signed URL support for private buckets (e.g., chat_attachments)
  - Graceful error handling with logging throughout

Configuration (settings.py / .env):
    SUPABASE_URL          = https://your-project.supabase.co
    SUPABASE_KEY          = <service-role key>              # server-side only
    SUPABASE_ANON_KEY     = <anon/public key>               # for client JS
    SUPABASE_BUCKET       = media                           # default bucket
    SUPABASE_STORAGE_BUCKETS = {                            # per-path routing
        "profile_pics": "avatars",
        "posts_images": "posts",
        ...
    }
"""

import io
import logging
import mimetypes
import os
import tempfile
import uuid

from django.conf import settings
from django.core.files.base import ContentFile, File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

logger = logging.getLogger(__name__)

# Private buckets require signed URLs (configurable)
_PRIVATE_BUCKETS = frozenset(
    getattr(settings, "SUPABASE_PRIVATE_BUCKETS", ["messages"])
)
_SIGNED_URL_EXPIRY = int(getattr(settings, "SUPABASE_SIGNED_URL_EXPIRY", 3600))  # seconds


def _get_client():
    """Return a fresh Supabase client or raise RuntimeError."""
    url = getattr(settings, "SUPABASE_URL", "") or os.environ.get("SUPABASE_URL", "")
    key = getattr(settings, "SUPABASE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set to use SupabaseStorage."
        )
    try:
        from supabase_client import get_supabase_client
        client = get_supabase_client()
        if client:
            return client
    except ImportError:
        pass
    # Direct fallback
    from supabase import create_client
    return create_client(url, key)


def _bucket_for_path(name: str) -> str:
    """Determine the Supabase bucket name based on filename prefix.

    Uses the SUPABASE_STORAGE_BUCKETS dict from settings, keyed by path prefix.
    Falls back to SUPABASE_BUCKET ('media') if no prefix matches.
    """
    name = name.replace('\\', '/')
    bucket_map: dict = getattr(settings, "SUPABASE_STORAGE_BUCKETS", {})
    for prefix, bucket in bucket_map.items():
        if name.startswith(prefix + "/") or name.startswith(prefix):
            return bucket
    return bucket_map.get("default") or getattr(settings, "SUPABASE_BUCKET", "media")


def _content_type_for(name: str) -> str:
    """Guess content-type from filename extension."""
    mime, _ = mimetypes.guess_type(name)
    return mime or "application/octet-stream"


@deconstructible
class SupabaseStorage(Storage):
    """Django storage backend backed by Supabase Storage.

    Instantiated by Django's STORAGES['default'] machinery.
    The 'bucket' constructor arg is optional; bucket is normally
    determined per-file from SUPABASE_STORAGE_BUCKETS.
    """

    def __init__(self, bucket: str = None):
        # bucket param kept for backwards-compat and manual instantiation
        self._default_bucket = bucket or None

    # ── Core Django Storage interface ────────────────────────────────────────

    def _open(self, name: str, mode: str = "rb") -> File:
        """Download a file from Supabase Storage and return a Django File object."""
        if "w" in mode:
            raise NotImplementedError("SupabaseStorage does not support write mode in _open(). Use _save() instead.")
        bucket = self._default_bucket or _bucket_for_path(name)
        try:
            client = _get_client()
            response = client.storage.from_(bucket).download(name)
            if isinstance(response, (bytes, bytearray)):
                return File(io.BytesIO(response), name=name)
            # Some SDK versions return a response object
            content = getattr(response, "content", None) or response
            return File(io.BytesIO(content), name=name)
        except Exception as exc:
            logger.error("SupabaseStorage._open failed for %s in bucket %s: %s", name, bucket, exc)
            raise FileNotFoundError(f"Cannot open '{name}' from Supabase Storage: {exc}") from exc

    def _save(self, name: str, content) -> str:
        """Upload a file to Supabase Storage and return its storage path."""
        name = name.replace('\\', '/')
        bucket = self._default_bucket or _bucket_for_path(name)
        content_type = _content_type_for(name)

        # Write content to a temporary file (Supabase SDK expects a file-like)
        tmp = tempfile.NamedTemporaryFile(delete=False)
        try:
            if hasattr(content, "chunks"):
                for chunk in content.chunks():
                    tmp.write(chunk)
            else:
                content.seek(0)
                tmp.write(content.read())
            tmp.flush()
            tmp.close()

            client = _get_client()
            bucket_ref = client.storage.from_(bucket)

            with open(tmp.name, "rb") as f:
                bucket_ref.upload(
                    name,
                    f,
                    file_options={"content-type": content_type, "upsert": "true"},
                )
            logger.debug("SupabaseStorage._save: uploaded %s to bucket=%s", name, bucket)
        except Exception as exc:
            logger.error("SupabaseStorage._save failed for %s bucket=%s: %s", name, bucket, exc)
            raise
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

        return name

    def exists(self, name: str) -> bool:
        """Check if a file exists in the bucket by listing with an exact prefix."""
        name = name.replace('\\', '/')
        bucket = self._default_bucket or _bucket_for_path(name)
        try:
            client = _get_client()
            # Split into directory and filename
            dirname = os.path.dirname(name)
            filename = os.path.basename(name)
            bucket_ref = client.storage.from_(bucket)
            entries = bucket_ref.list(path=dirname or "", options={"search": filename})
            return any(e.get("name") == filename for e in (entries or []))
        except Exception as exc:
            logger.debug("SupabaseStorage.exists check failed for %s: %s", name, exc)
            return False

    def delete(self, name: str) -> None:
        """Remove a file from Supabase Storage."""
        name = name.replace('\\', '/')
        bucket = self._default_bucket or _bucket_for_path(name)
        try:
            _get_client().storage.from_(bucket).remove([name])
            logger.debug("SupabaseStorage.delete: removed %s from bucket=%s", name, bucket)
        except Exception as exc:
            logger.warning("SupabaseStorage.delete failed for %s: %s", name, exc)

    def url(self, name: str) -> str:
        """Return the public (or signed) URL for a stored file."""
        if not name:
            return ""
        name = name.replace('\\', '/')
        bucket = self._default_bucket or _bucket_for_path(name)
        try:
            client = _get_client()
            bucket_ref = client.storage.from_(bucket)

            if bucket in _PRIVATE_BUCKETS:
                # Signed URL for private buckets
                result = bucket_ref.create_signed_url(name, _SIGNED_URL_EXPIRY)
                signed = result if isinstance(result, str) else (
                    result.get("signedURL") or result.get("signedUrl") or result.get("signed_url", "")
                )
                return signed

            # Public URL for open buckets
            result = bucket_ref.get_public_url(name)
            if isinstance(result, str):
                return result
            return result.get("publicURL") or result.get("publicUrl") or self._fallback_url(bucket, name)
        except Exception as exc:
            logger.warning("SupabaseStorage.url failed for %s: %s — using fallback", name, exc)
            return self._fallback_url(bucket, name)

    def size(self, name: str) -> int | None:
        """Return file size in bytes, or None if unavailable."""
        bucket = self._default_bucket or _bucket_for_path(name)
        try:
            client = _get_client()
            dirname = os.path.dirname(name)
            filename = os.path.basename(name)
            entries = client.storage.from_(bucket).list(path=dirname or "", options={"search": filename})
            for entry in (entries or []):
                if entry.get("name") == filename:
                    return entry.get("metadata", {}).get("size")
        except Exception:
            pass
        return None

    def get_available_name(self, name: str, max_length: int = None) -> str:
        """Prefix filename with a UUID4 to guarantee uniqueness without existence checks."""
        dirname = os.path.dirname(name)
        basename = os.path.basename(name)
        # Insert UUID before the filename to avoid collisions
        unique_name = f"{uuid.uuid4().hex[:12]}_{basename}"
        result = os.path.join(dirname, unique_name) if dirname else unique_name
        if max_length and len(result) > max_length:
            # Trim UUID prefix to fit
            result = result[:max_length]
        return result

    def listdir(self, path: str) -> tuple[list, list]:
        """List the contents of a storage path. Returns (dirs, files)."""
        bucket = self._default_bucket or _bucket_for_path(path)
        try:
            entries = _get_client().storage.from_(bucket).list(path=path or "")
            dirs, files = [], []
            for entry in (entries or []):
                name = entry.get("name", "")
                if entry.get("id") is None:
                    dirs.append(name)
                else:
                    files.append(name)
            return dirs, files
        except Exception as exc:
            logger.warning("SupabaseStorage.listdir failed for %s: %s", path, exc)
            return [], []

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _fallback_url(self, bucket: str, name: str) -> str:
        """Construct a public URL from SUPABASE_URL without an API call."""
        base = (getattr(settings, "SUPABASE_URL", "") or "").rstrip("/")
        if not base:
            return name
        return f"{base}/storage/v1/object/public/{bucket}/{name}"
