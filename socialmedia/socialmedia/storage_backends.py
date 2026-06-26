import os
import tempfile
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from supabase import create_client


class SupabaseStorage(Storage):
    """A minimal Django storage backend using Supabase Storage.

    Notes:
    - Requires `SUPABASE_URL` and `SUPABASE_KEY` in environment.
    - Optional `SUPABASE_BUCKET` env var (defaults to "media").
    - This implementation writes an upload to a temporary file and uses
      the Supabase Python client to upload it. It implements the
      methods Django's file handling needs: `_save`, `exists`, `url`, `delete`.
    """

    def __init__(self, bucket=None):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_KEY")
        if not self.url or not self.key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set to use SupabaseStorage")
        self.client = create_client(self.url, self.key)
        self.bucket = bucket or os.environ.get("SUPABASE_BUCKET", "media")

    def _open(self, name, mode='rb'):
        # Not implemented: reading from Supabase storage via SDK is possible,
        # but Django rarely needs to open uploaded files from storage backend.
        raise NotImplementedError("Opening files from SupabaseStorage is not implemented")

    def _save(self, name, content):
        # Write content to a temp file because supabase.storage.upload expects a file-like
        tmp = tempfile.NamedTemporaryFile(delete=False)
        try:
            if hasattr(content, 'chunks'):
                for chunk in content.chunks():
                    tmp.write(chunk)
            else:
                tmp.write(content.read())
            tmp.flush()
            tmp.close()

            # Upload using Supabase client
            bucket = self.client.storage.from_(self.bucket)
            with open(tmp.name, 'rb') as f:
                # The SDK supports upload(path, file)
                bucket.upload(name, f)

        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

        return name

    def exists(self, name):
        try:
            bucket = self.client.storage.from_(self.bucket)
            res = bucket.list(prefix=name)
            # list returns entries when the object exists
            return bool(res)
        except Exception:
            return False

    def url(self, name):
        # Return the public URL for the object; if object is private, generate signed URL instead.
        bucket = self.client.storage.from_(self.bucket)
        try:
            public = bucket.get_public_url(name)
            # SDK returns {'publicURL': 'https://...'} in many versions
            if isinstance(public, dict):
                return public.get('publicURL') or public.get('public_url')
            return public
        except Exception:
            # Fallback: construct URL from SUPABASE_URL
            base = os.environ.get('SUPABASE_URL').rstrip('/')
            return f"{base}/storage/v1/object/public/{self.bucket}/{name}"

    def delete(self, name):
        bucket = self.client.storage.from_(self.bucket)
        try:
            bucket.remove([name])
        except Exception:
            pass

    def size(self, name):
        # Not implemented; return None to indicate unknown size
        return None
