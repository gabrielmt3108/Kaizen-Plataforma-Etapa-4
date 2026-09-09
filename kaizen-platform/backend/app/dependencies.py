from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db
from app.models import User


bearer_scheme = HTTPBearer(auto_error=False)
Database = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: Database,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autenticação necessária.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise unauthorized
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as error:
        raise unauthorized from error
    user = await db.get(User, payload["sub"])
    if (
        not user
        or not user.is_active
        or int(payload.get("ver", 0)) != user.token_version
    ):
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

