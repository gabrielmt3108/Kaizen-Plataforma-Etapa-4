from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_verification_code,
    hash_refresh_token,
    hash_verification_code,
    verify_verification_code,
)
from app.models import RefreshSession, User, VerificationChallenge
from app.schemas import AuthResponse, UserOut
from app.services.delivery import deliver_code


GENERIC_RECOVERY_MESSAGE = (
    "Se os dados corresponderem a uma conta, um código de recuperação será enviado."
)


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Normaliza datas que o SQLite pode devolver sem informação de fuso."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def find_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email))


async def find_user_by_phone(db: AsyncSession, phone: str) -> User | None:
    return await db.scalar(select(User).where(User.phone == phone))


def set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=raw_token,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=f"{settings.api_prefix}/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=f"{settings.api_prefix}/auth",
    )


async def issue_authentication(
    db: AsyncSession,
    user: User,
    response: Response,
    request: Request,
) -> AuthResponse:
    # Garante que o ID padrão de um usuário recém-criado já exista.
    await db.flush()
    raw_refresh, refresh_hash = create_refresh_token()
    refresh_session = RefreshSession(
        user_id=user.id,
        token_hash=refresh_hash,
        user_agent=(request.headers.get("user-agent") or "")[:300] or None,
        expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
    )
    db.add(refresh_session)
    access_token, expires_in = create_access_token(user.id, user.token_version)
    await db.commit()
    set_refresh_cookie(response, raw_refresh)
    return AuthResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserOut.model_validate(user),
    )


async def revoke_all_user_sessions(db: AsyncSession, user_id: str) -> None:
    await db.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


async def create_challenge(
    db: AsyncSession,
    *,
    identifier: str,
    channel: str,
    purpose: str,
    user: User | None,
    requested_name: str | None = None,
) -> str:
    code = create_verification_code()
    challenge = VerificationChallenge(
        user_id=user.id if user else None,
        identifier=identifier,
        channel=channel,
        purpose=purpose,
        requested_name=requested_name,
        code_hash=hash_verification_code(identifier, code),
        expires_at=utcnow() + timedelta(minutes=settings.recovery_code_minutes),
    )
    db.add(challenge)
    try:
        await db.flush()
        await deliver_code(channel, identifier, code)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return code


async def consume_challenge(
    db: AsyncSession,
    *,
    identifier: str,
    purpose: str,
    code: str,
) -> VerificationChallenge:
    challenge = await db.scalar(
        select(VerificationChallenge)
        .where(
            VerificationChallenge.identifier == identifier,
            VerificationChallenge.purpose == purpose,
            VerificationChallenge.consumed_at.is_(None),
        )
        .order_by(VerificationChallenge.created_at.desc())
        .limit(1)
    )
    if not challenge or as_utc(challenge.expires_at) <= utcnow() or challenge.attempts >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado.",
        )
    if not verify_verification_code(identifier, code, challenge.code_hash):
        challenge.attempts += 1
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado.",
        )
    challenge.consumed_at = utcnow()
    await db.flush()
    return challenge


async def rotate_refresh_session(
    db: AsyncSession,
    raw_refresh: str,
    response: Response,
    request: Request,
) -> AuthResponse:
    token_hash = hash_refresh_token(raw_refresh)
    refresh_session = await db.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == token_hash)
    )
    if (
        not refresh_session
        or refresh_session.revoked_at is not None
        or as_utc(refresh_session.expires_at) <= utcnow()
    ):
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida.")
    user = await db.get(User, refresh_session.user_id)
    if not user or not user.is_active:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Conta indisponível.")
    refresh_session.revoked_at = utcnow()
    await db.flush()
    return await issue_authentication(db, user, response, request)
