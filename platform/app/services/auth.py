"""Auth + encryption primitives.

Password hashing: bcrypt directly (passlib 1.7.4 incompatible with bcrypt 5.x)
JWT: HS256 via python-jose
Encryption (Anthropic API keys etc.): AES-GCM via cryptography
"""

import base64
import datetime as dt
import secrets
from typing import Any

import bcrypt
from jose import jwt, JWTError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings


# --- Passwords ---
# bcrypt has 72-byte plaintext limit; we truncate consistently on both sides.
# For practical purposes passwords < 72 chars and we don't lose entropy.

def _truncate(plaintext: str) -> bytes:
    return plaintext.encode("utf-8")[:72]


def hash_password(plaintext: str) -> str:
    return bcrypt.hashpw(_truncate(plaintext), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_truncate(plaintext), hashed.encode("utf-8"))
    except Exception:
        return False


# --- JWT ---

def create_access_token(user_id: int, email: str, extra: dict[str, Any] | None = None) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(minutes=settings.jwt_access_ttl_minutes)).timestamp()),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


# --- AES-GCM encryption for sensitive fields (API keys) ---

def _get_key() -> bytes:
    raw = base64.b64decode(settings.encryption_key_b64)
    if len(raw) < 16:
        raise RuntimeError(
            "FORGE_ENCRYPTION_KEY too short — provide a base64-encoded 32-byte key "
            "(e.g. `python -c \"import os,base64; print(base64.b64encode(os.urandom(32)).decode())\"`)"
        )
    # AES-GCM wymaga 16/24/32 bajty. Jeśli dłuższy niż 32 — bierzemy pierwsze 32.
    # Jeśli krótszy niż 32 ale ≥16 — używamy jak jest.
    if len(raw) >= 32:
        return raw[:32]
    elif len(raw) >= 24:
        return raw[:24]
    return raw[:16]


def encrypt_secret(plaintext: str) -> str:
    """Encrypt string → base64(nonce || ciphertext). Returns empty string for empty input."""
    if not plaintext:
        return ""
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt_secret(ciphertext_b64: str) -> str | None:
    """Decrypt base64(nonce||ct) → plaintext. Returns None on failure (bad key, tampered, wrong format)."""
    if not ciphertext_b64:
        return None
    try:
        blob = base64.b64decode(ciphertext_b64)
        if len(blob) < 13:
            return None
        nonce, ct = blob[:12], blob[12:]
        aesgcm = AESGCM(_get_key())
        pt = aesgcm.decrypt(nonce, ct, associated_data=None)
        return pt.decode("utf-8")
    except Exception:
        return None
