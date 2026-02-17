# backend/app/core/auth.py
"""
Supabase Auth JWT validation for FastAPI.

Extracts the Bearer token from the Authorization header,
validates it against the Supabase JWT secret, and returns
the authenticated user's UUID.
"""
from __future__ import annotations

import logging
from typing import Any, Dict
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

from app.config import Settings, get_settings

logger = logging.getLogger("promptvault.auth")


def _extract_token(request: Request) -> str:
    """Pull the Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    return auth_header[7:]


def _decode_jwt(token: str, settings: Settings) -> Dict[str, Any]:
    """Decode and validate a Supabase-issued JWT."""
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except JWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_current_user_id(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> UUID:
    """
    FastAPI dependency — returns the authenticated user's UUID.
    Use as: user_id: UUID = Depends(get_current_user_id)
    """
    token = _extract_token(request)
    payload = _decode_jwt(token, settings)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim",
        )
    return UUID(sub)


async def get_access_token(request: Request) -> str:
    """
    FastAPI dependency — returns the raw access token string.
    Used to create user-scoped Supabase clients.
    """
    return _extract_token(request)
