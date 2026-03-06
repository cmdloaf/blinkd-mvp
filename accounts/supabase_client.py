from django.conf import settings
from supabase import Client, create_client

_client: Client | None = None
_admin_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    return _client


def get_supabase_admin() -> Client:
    """Service-role client for server-side storage operations (bypasses RLS)."""
    global _admin_client
    if _admin_client is None:
        _admin_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _admin_client
