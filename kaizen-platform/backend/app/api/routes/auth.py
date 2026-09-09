from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.identifiers import normalize_email, validate_email, validate_phone
from app.core.security import hash_password, hash_refresh_token, verify_password
from app.dependencies import CurrentUser, Database
from app.models import RefreshSession, User
from app.schemas import (
    AuthResponse,
    CodeConfirmRequest,
    LoginRequest,
    MessageResponse,
    PhoneCodeRequest,
    PhoneCodeVerifyRequest,
    RecoveryConfirmRequest,
    RecoveryRequest,
    RegisterRequest,
    UserOut,
)
from app.services.auth_service import (
    GENERIC_RECOVERY_MESSAGE,
    clear_refresh_cookie,
    consume_challenge,
    create_challenge,
    find_user_by_email,
    find_user_by_phone,
    issue_authentication,
    revoke_all_user_sessions,
    rotate_refresh_session,
    utcnow,
)


router = APIRouter(prefix="/auth", tags=["autenticação"])


def bad_identifier(error: ValueError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(error),
    )


def password_hash_or_422(password: str) -> str:
    try:
        return hash_password(password)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error


def normalize_recovery_identifier(channel: str, identifier: str) -> str:
    try:
        if channel == "email":
            return validate_email(identifier)
        return validate_phone(identifier)
    except ValueError as error:
        raise bad_identifier(error) from error


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: Database,
    response: Response,
    request: Request,
) -> AuthResponse:
    email = normalize_email(str(payload.email))
    if await find_user_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta com esse e-mail.",
        )

    user = User(
        name=payload.name,
        email=email,
        password_hash=password_hash_or_422(payload.password),
        auth_provider="email",
        is_verified=False,
    )
    db.add(user)
    try:
        return await issue_authentication(db, user, response, request)
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta com esse e-mail.",
        ) from error


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    db: Database,
    response: Response,
    request: Request,
) -> AuthResponse:
    email = normalize_email(str(payload.email))
    user = await find_user_by_email(db, email)
    if (
        not user
        or not user.password_hash
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
        )
    return await issue_authentication(db, user, response, request)


@router.post("/email/verification/request", response_model=MessageResponse)
async def request_email_verification(user: CurrentUser, db: Database) -> MessageResponse:
    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Essa conta não possui e-mail.",
        )
    if user.is_verified:
        return MessageResponse(message="E-mail já verificado.")
    code = await create_challenge(
        db,
        identifier=user.email,
        channel="email",
        purpose="email_verification",
        user=user,
    )
    return MessageResponse(
        message="Código de verificação enviado.",
        debug_code=code if settings.debug else None,
    )


@router.post("/email/verification/confirm", response_model=MessageResponse)
async def confirm_email_verification(
    payload: CodeConfirmRequest,
    user: CurrentUser,
    db: Database,
) -> MessageResponse:
    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Essa conta não possui e-mail.",
        )
    if user.is_verified:
        return MessageResponse(message="E-mail já verificado.")
    challenge = await consume_challenge(
        db,
        identifier=user.email,
        purpose="email_verification",
        code=payload.code,
    )
    if challenge.user_id != user.id:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado.",
        )
    user.is_verified = True
    await db.commit()
    return MessageResponse(message="E-mail verificado com sucesso.")


@router.post("/phone/request", response_model=MessageResponse)
async def request_phone_code(payload: PhoneCodeRequest, db: Database) -> MessageResponse:
    try:
        phone = validate_phone(payload.phone)
    except ValueError as error:
        raise bad_identifier(error) from error
    user = await find_user_by_phone(db, phone)
    code = await create_challenge(
        db,
        identifier=phone,
        channel="phone",
        purpose="phone_login",
        user=user,
        requested_name=payload.name,
    )
    return MessageResponse(
        message="Código enviado. Ele expira em poucos minutos.",
        debug_code=code if settings.debug else None,
    )


@router.post("/phone/verify", response_model=AuthResponse)
async def verify_phone_code(
    payload: PhoneCodeVerifyRequest,
    db: Database,
    response: Response,
    request: Request,
) -> AuthResponse:
    try:
        phone = validate_phone(payload.phone)
    except ValueError as error:
        raise bad_identifier(error) from error

    challenge = await consume_challenge(
        db,
        identifier=phone,
        purpose="phone_login",
        code=payload.code,
    )
    user = await find_user_by_phone(db, phone)
    if not user:
        if not challenge.requested_name:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Informe seu nome ao solicitar o primeiro código.",
            )
        user = User(
            name=challenge.requested_name,
            phone=phone,
            auth_provider="phone",
            is_verified=True,
        )
        db.add(user)
    else:
        user.is_verified = True

    try:
        return await issue_authentication(db, user, response, request)
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível concluir o acesso com esse telefone.",
        ) from error


@router.post("/recovery/request", response_model=MessageResponse)
async def request_recovery(payload: RecoveryRequest, db: Database) -> MessageResponse:
    identifier = normalize_recovery_identifier(payload.channel, payload.identifier)
    if payload.channel == "email":
        user = await find_user_by_email(db, identifier)
    else:
        user = await find_user_by_phone(db, identifier)

    code: str | None = None
    if user:
        code = await create_challenge(
            db,
            identifier=identifier,
            channel=payload.channel,
            purpose="password_recovery",
            user=user,
        )
    return MessageResponse(
        message=GENERIC_RECOVERY_MESSAGE,
        debug_code=code if settings.debug else None,
    )


@router.post("/recovery/confirm", response_model=AuthResponse)
async def confirm_recovery(
    payload: RecoveryConfirmRequest,
    db: Database,
    response: Response,
    request: Request,
) -> AuthResponse:
    identifier = normalize_recovery_identifier(payload.channel, payload.identifier)
    challenge = await consume_challenge(
        db,
        identifier=identifier,
        purpose="password_recovery",
        code=payload.code,
    )
    user = await db.get(User, challenge.user_id) if challenge.user_id else None
    if not user or not user.is_active:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado.",
        )

    if payload.channel == "email":
        if not payload.new_password:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Informe a nova senha.",
            )
        user.password_hash = password_hash_or_422(payload.new_password)
        user.is_verified = True
    user.token_version += 1
    await revoke_all_user_sessions(db, user.id)
    return await issue_authentication(db, user, response, request)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    db: Database,
    response: Response,
    request: Request,
    refresh_token: Annotated[
        str | None,
        Cookie(alias=settings.refresh_cookie_name),
    ] = None,
) -> AuthResponse:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão ausente.")
    return await rotate_refresh_session(db, refresh_token, response, request)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    db: Database,
    response: Response,
    refresh_token: Annotated[
        str | None,
        Cookie(alias=settings.refresh_cookie_name),
    ] = None,
) -> MessageResponse:
    if refresh_token:
        token_hash = hash_refresh_token(refresh_token)
        refresh_session = await db.scalar(
            select(RefreshSession).where(RefreshSession.token_hash == token_hash)
        )
        if refresh_session:
            refresh_session.revoked_at = utcnow()
            await db.commit()
    clear_refresh_cookie(response)
    return MessageResponse(message="Sessão encerrada.")


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
