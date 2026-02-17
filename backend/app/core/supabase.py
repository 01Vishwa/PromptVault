# backend/app/core/supabase.py
"""
Supabase client factory.

Two clients:
  - anon_client:         uses the anon key, for RLS-scoped access with user JWT
  - service_client:      uses the service_role key, bypasses RLS (for /serve endpoint)
"""
from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache()
def get_supabase_client() -> Client:
    """
    Returns a Supabase client using the service_role key.
    Use this for server-side operations that bypass RLS
    (e.g., the public /serve endpoint, background tasks).
    """
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def get_user_client(access_token: str) -> Client:
    """
    Returns a Supabase client scoped to a specific user's JWT.
    All queries go through RLS as that user.
    """
    settings = get_settings()
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    client.auth.set_session(access_token, "")  # type: ignore[arg-type]
    client.postgrest.auth(access_token)
    return client
