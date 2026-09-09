import secrets

from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import settings
from app.dependencies import Database
from app.services.notification_dispatcher import dispatch_due_notifications

router = APIRouter(prefix="/internal", tags=["interno"])


@router.post("/notifications/dispatch", include_in_schema=False)
async def dispatch_notifications(request: Request, db: Database) -> dict[str, int | str]:
    if not settings.notification_cron_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rota não disponível.")

    provided_secret = request.headers.get("x-kaizen-cron-secret", "")
    if not provided_secret or not secrets.compare_digest(provided_secret, settings.cron_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial do agendador inválida.",
        )

    sent = await dispatch_due_notifications(db)
    return {"status": "ok", "sent_devices": sent}
