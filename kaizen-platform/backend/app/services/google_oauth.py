import base64
import hashlib
import secrets
from datetime import timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
import jwt
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.identifiers import normalize_email
from app.models import (
    NotificationDevice,
    OAuthExchangeCode,
    OAuthIdentity,
    OAuthLoginAttempt,
    User,
)
from app.services.auth_service import (
    as_utc,
    find_user_by_email,
    revoke_all_user_sessions,
    utcnow,
)


GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_ENDPOINT = "https://www.googleapis.com/oauth2/v3/certs"


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def validated_return_to(value: str) -> str:
    if len(value) > 1000:
        raise HTTPException(status_code=422, detail="Endereço de retorno inválido.")
    parsed = urlsplit(value)
    if (
        parsed.username
        or parsed.password
        or parsed.fragment
        or not parsed.scheme
        or not parsed.netloc
    ):
        raise HTTPException(status_code=422, detail="Endereço de retorno inválido.")
    origin = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}".rstrip("/")
    allowed = {item.lower() for item in settings.oauth_return_origin_list}
    if origin not in allowed:
        raise HTTPException(status_code=422, detail="Origem de retorno não autorizada.")
    return value


def add_return_parameter(return_to: str, key: str, value: str) -> str:
    parsed = urlsplit(return_to)
    query = [(name, item) for name, item in parse_qsl(parsed.query) if name != key]
    query.append((key, value))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


async def begin_google_login(db: AsyncSession, return_to: str) -> str:
    if not settings.google_oauth_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="O acesso com Google ainda não foi configurado neste ambiente.",
        )
    safe_return_to = validated_return_to(return_to)
    raw_state = secrets.token_urlsafe(48)
    nonce = secrets.token_urlsafe(48)
    verifier = secrets.token_urlsafe(64)
    attempt = OAuthLoginAttempt(
        state_hash=token_hash(raw_state),
        nonce=nonce,
        code_verifier=verifier,
        return_to=safe_return_to,
        expires_at=utcnow() + timedelta(minutes=settings.oauth_attempt_minutes),
    )
    db.add(attempt)
    await db.commit()
    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": raw_state,
            "nonce": nonce,
            "code_challenge": pkce_challenge(verifier),
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
    )
    return f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{query}"


async def _validated_google_claims(id_token: str, expected_nonce: str) -> dict:
    try:
        header = jwt.get_unverified_header(id_token)
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(GOOGLE_JWKS_ENDPOINT)
            response.raise_for_status()
        jwks = response.json().get("keys", [])
        jwk_data = next(item for item in jwks if item.get("kid") == header.get("kid"))
        signing_key = jwt.PyJWK.from_dict(jwk_data).key
        claims = jwt.decode(
            id_token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.google_client_id,
            issuer=["accounts.google.com", "https://accounts.google.com"],
            options={"require": ["exp", "iat", "iss", "aud", "sub", "email"]},
        )
    except (httpx.HTTPError, jwt.PyJWTError, KeyError, StopIteration, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Resposta de identidade do Google inválida.",
        ) from None
    if not secrets.compare_digest(str(claims.get("nonce", "")), expected_nonce):
        raise HTTPException(status_code=400, detail="Resposta de identidade do Google inválida.")
    if claims.get("email_verified") is not True:
        raise HTTPException(status_code=400, detail="O Google não confirmou este e-mail.")
    return claims


async def _exchange_google_token(code: str, attempt: OAuthLoginAttempt) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "code": code,
                    "code_verifier": attempt.code_verifier,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.google_redirect_uri,
                },
            )
            response.raise_for_status()
        token_data = response.json()
        return await _validated_google_claims(token_data["id_token"], attempt.nonce)
    except (httpx.HTTPError, KeyError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Não foi possível validar o acesso do Google.",
        ) from None


async def _user_for_google_claims(db: AsyncSession, claims: dict) -> User:
    subject = str(claims["sub"])
    identity = await db.scalar(
        select(OAuthIdentity).where(
            OAuthIdentity.provider == "google",
            OAuthIdentity.subject == subject,
        )
    )
    if identity:
        user = await db.get(User, identity.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=403, detail="Conta indisponível.")
        return user

    email = normalize_email(str(claims["email"]))
    user = await find_user_by_email(db, email)
    if not user:
        name = " ".join(str(claims.get("name") or email.split("@", 1)[0]).split())[:80]
        user = User(
            name=name or "Pessoa Kaizen",
            email=email,
            auth_provider="google",
            is_verified=True,
        )
        db.add(user)
        await db.flush()
    else:
        existing_provider = await db.scalar(
            select(OAuthIdentity).where(
                OAuthIdentity.user_id == user.id,
                OAuthIdentity.provider == "google",
            )
        )
        if existing_provider:
            raise HTTPException(
                status_code=409,
                detail="Esta conta já está vinculada a outro acesso do Google.",
            )
        if not user.is_verified:
            # Impede que um cadastro antecipado com e-mail alheio mantenha senha,
            # sessão ou dispositivo push depois que o titular prova o e-mail no Google.
            user.password_hash = None
            user.token_version += 1
            await revoke_all_user_sessions(db, user.id)
            await db.execute(
                update(NotificationDevice)
                .where(NotificationDevice.user_id == user.id)
                .values(is_active=False)
            )
            user.auth_provider = "google"
        else:
            user.auth_provider = "multiple" if user.password_hash or user.phone else "google"
        user.is_verified = True
    db.add(OAuthIdentity(user_id=user.id, provider="google", subject=subject, email=email))
    return user


async def complete_google_login(db: AsyncSession, state: str, code: str) -> tuple[str, str]:
    attempt = await db.scalar(
        select(OAuthLoginAttempt)
        .where(OAuthLoginAttempt.state_hash == token_hash(state))
        .with_for_update()
    )
    if (
        not attempt
        or attempt.consumed_at is not None
        or as_utc(attempt.expires_at) <= utcnow()
    ):
        raise HTTPException(status_code=400, detail="Tentativa de acesso inválida ou expirada.")
    attempt.consumed_at = utcnow()
    await db.flush()
    claims = await _exchange_google_token(code, attempt)
    try:
        user = await _user_for_google_claims(db, claims)
        await db.flush()
        raw_exchange = secrets.token_urlsafe(48)
        db.add(
            OAuthExchangeCode(
                user_id=user.id,
                token_hash=token_hash(raw_exchange),
                expires_at=utcnow() + timedelta(minutes=settings.oauth_exchange_minutes),
            )
        )
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Não foi possível vincular esta conta.",
        ) from error
    return attempt.return_to, raw_exchange


async def cancel_google_login(db: AsyncSession, state: str) -> str:
    attempt = await db.scalar(
        select(OAuthLoginAttempt)
        .where(OAuthLoginAttempt.state_hash == token_hash(state))
        .with_for_update()
    )
    if (
        not attempt
        or attempt.consumed_at is not None
        or as_utc(attempt.expires_at) <= utcnow()
    ):
        raise HTTPException(status_code=400, detail="Tentativa de acesso inválida ou expirada.")
    attempt.consumed_at = utcnow()
    await db.commit()
    return attempt.return_to


async def consume_exchange_code(db: AsyncSession, raw_code: str) -> User:
    exchange = await db.scalar(
        select(OAuthExchangeCode)
        .where(OAuthExchangeCode.token_hash == token_hash(raw_code))
        .with_for_update()
    )
    if (
        not exchange
        or exchange.consumed_at is not None
        or as_utc(exchange.expires_at) <= utcnow()
    ):
        raise HTTPException(status_code=400, detail="Código de acesso inválido ou expirado.")
    user = await db.get(User, exchange.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Conta indisponível.")
    exchange.consumed_at = utcnow()
    await db.flush()
    return user
