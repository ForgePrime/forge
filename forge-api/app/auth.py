"""Authentication — API key + JWT token support."""

from __future__ import annotations

import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security schemes
# ---------------------------------------------------------------------------

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)

# Sentinel for unconfigured JWT secret
_DEFAULT_JWT_SECRET = ""

VALID_ROLES = {"admin", "user", "readonly"}


def _is_auth_configured() -> bool:
    """Check if authentication is configured (non-default secrets)."""
    return bool(settings.api_key) or (
        bool(settings.jwt_secret) and settings.jwt_secret != _DEFAULT_JWT_SECRET
    )


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token. Raises JWTError on failure."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


# ---------------------------------------------------------------------------
# Auth dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    request: Request,
    api_key: str | None = Security(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict[str, Any]:
    """Authenticate the request via API key or JWT bearer token.

    Returns a user dict with at least {"sub": ..., "auth_method": ...}.
    If no auth is configured, all requests pass (dev mode).
    """
    # If no auth configured, allow all requests (development mode)
    if not _is_auth_configured():
        return {"sub": "anonymous", "auth_method": "none"}

    # Try API key first (F-01: timing-safe comparison)
    if api_key:
        if not settings.api_key:
            raise HTTPException(401, "Authentication failed")
        if hmac.compare_digest(api_key, settings.api_key):
            return {"sub": "api-key-user", "auth_method": "api_key", "role": "admin"}
        logger.warning("Invalid API key attempt from %s", request.client.host if request.client else "unknown")
        raise HTTPException(401, "Authentication failed")

    # Try JWT bearer token
    if bearer:
        try:
            payload = decode_access_token(bearer.credentials)
            sub = payload.get("sub")
            if sub is None:
                raise HTTPException(401, "Authentication failed")
            role = payload.get("role", "user")
            if role not in VALID_ROLES:
                raise HTTPException(401, "Authentication failed")
            return {
                "sub": sub,
                "auth_method": "jwt",
                "role": role,
            }
        except JWTError:
            raise HTTPException(401, "Authentication failed")

    # No credentials provided — auth is required
    raise HTTPException(
        401,
        "Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_auth(user: dict = Depends(get_current_user)) -> dict:
    """Strict auth — always require valid credentials (no anonymous fallback)."""
    if user.get("auth_method") == "none":
        raise HTTPException(
            401,
            "Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
