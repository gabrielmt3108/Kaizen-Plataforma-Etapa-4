import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.core.password_policy import require_strong_password


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    require_strong_password(password)
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: str, token_version: int) -> tuple[str, int]:
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.access_token_minutes)
    payload = {
        "sub": user_id,
        "typ": "access",
        "ver": token_version,
        "iat": now,
        "exp": expires,
        "jti": str(uuid4()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int((expires - now).total_seconds())


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("typ") != "access" or not payload.get("sub"):
        raise jwt.InvalidTokenError("Tipo de token inválido")
    return payload


def create_refresh_token() -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(48)
    return raw_token, hash_refresh_token(raw_token)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_verification_code(identifier: str, code: str) -> str:
    message = f"{identifier}|{code}".encode("utf-8")
    return hmac.new(settings.jwt_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_verification_code(identifier: str, code: str, expected_hash: str) -> bool:
    candidate = hash_verification_code(identifier, code)
    return hmac.compare_digest(candidate, expected_hash)

