from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.dependencies import Database


router = APIRouter(tags=["saúde"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(db: Database) -> dict[str, str]:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponível.",
        ) from error
    return {"status": "ready"}
