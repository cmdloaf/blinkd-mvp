import os
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage


class SupabaseStorage(Storage):
    """Django file storage backend backed by Supabase Storage."""

    def __init__(self):
        self.bucket = settings.SUPABASE_STORAGE_BUCKET

    @property
    def _client(self):
        from accounts.supabase_client import get_supabase_admin
        return get_supabase_admin()

    def _save(self, name, content):
        ext = os.path.splitext(name)[1].lower()
        unique_name = f"screenshots/{uuid.uuid4().hex}{ext}"
        file_bytes = content.read()
        content_type = getattr(content, "content_type", None) or "application/octet-stream"
        self._client.storage.from_(self.bucket).upload(
            unique_name,
            file_bytes,
            {"content-type": content_type, "upsert": "false"},
        )
        return unique_name

    def url(self, name):
        return self._client.storage.from_(self.bucket).get_public_url(name)

    def exists(self, name):
        try:
            folder = os.path.dirname(name)
            filename = os.path.basename(name)
            res = self._client.storage.from_(self.bucket).list(folder)
            return any(f.get("name") == filename for f in (res or []))
        except Exception:
            return False

    def delete(self, name):
        try:
            self._client.storage.from_(self.bucket).remove([name])
        except Exception:
            pass

    def _open(self, name, mode="rb"):
        file_bytes = self._client.storage.from_(self.bucket).download(name)
        return ContentFile(file_bytes)

    def get_valid_name(self, name):
        return name

    def get_available_name(self, name, max_length=None):
        # _save always generates a unique UUID path, so no collision checking needed
        return name
