from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import RedirectResponse

from app.dependencies import Database
from app.schemas import AuthResponse, GoogleOAuthExchangeRequest, GoogleOAuthStartOut
from app.services.auth_service import issue_authentication
from app.services.google_oauth import (
    add_return_parameter,
    begin_google_login,
    cancel_google_login,
    complete_google_login,
    consume_exchange_code,
)


router = APIRouter(prefix="/auth/google", tags=["autenticação"])


@router.get("/start", response_model=GoogleOAuthStartOut)
async def google_start(return_to: str, db: Database) -> GoogleOAuthStartOut:
    return GoogleOAuthStartOut(authorization_url=await begin_google_login(db, return_to))


@router.get("/callback", include_in_schema=False)
async def google_callback(
    db: Database,
    state: str = Query(min_length=32, max_length=512),
    code: str | None = Query(default=None, min_length=1, max_length=4096),
    error: str | None = Query(default=None, max_length=100),
) -> RedirectResponse:
    if error or not code:
        return_to = await cancel_google_login(db, state)
        return RedirectResponse(
            add_return_parameter(return_to, "oauth_error", "access_denied"),
            status_code=303,
        )
    return_to, exchange_code = await complete_google_login(db, state, code)
    return RedirectResponse(
        add_return_parameter(return_to, "oauth_code", exchange_code),
        status_code=303,
    )


@router.post("/exchange", response_model=AuthResponse)
async def google_exchange(
    payload: GoogleOAuthExchangeRequest,
    db: Database,
    response: Response,
    request: Request,
) -> AuthResponse:
    user = await consume_exchange_code(db, payload.code)
    return await issue_authentication(db, user, response, request)
