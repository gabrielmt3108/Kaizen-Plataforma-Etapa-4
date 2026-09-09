import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import NotificationDevice
from app.notification_schemas import NotificationPayload

logger = logging.getLogger("kaizen.notifications")
_firebase_app = None


class ProviderConfigurationError(RuntimeError):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


def web_push_subscription(device: NotificationDevice) -> dict:
    return {
        "endpoint": device.endpoint,
        "keys": {"p256dh": device.p256dh, "auth": device.auth},
    }


def notification_json(payload: NotificationPayload) -> str:
    return json.dumps(
        {
            "title": payload.title,
            "body": payload.body,
            "url": payload.url,
            "type": payload.notification_type,
            "tag": payload.tag or payload.notification_type,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def send_web_push(device: NotificationDevice, payload: NotificationPayload) -> None:
    if not settings.web_push_enabled:
        raise ProviderConfigurationError("Web Push não está configurado no servidor")
    from pywebpush import webpush

    webpush(
        subscription_info=web_push_subscription(device),
        data=notification_json(payload),
        vapid_private_key=settings.vapid_private_key,
        vapid_claims={"sub": settings.vapid_subject},
        ttl=3600,
    )


def get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app
    if not settings.firebase_credentials_path and not settings.firebase_credentials_json:
        raise ProviderConfigurationError("Firebase não está configurado no servidor")
    import firebase_admin
    from firebase_admin import credentials

    if settings.firebase_credentials_json:
        try:
            credential_source = json.loads(settings.firebase_credentials_json)
        except json.JSONDecodeError as error:
            raise ProviderConfigurationError(
                "O JSON de credenciais do Firebase é inválido"
            ) from error
    else:
        credentials_path = Path(settings.firebase_credentials_path)
        if not credentials_path.is_file():
            raise ProviderConfigurationError("Arquivo de credenciais do Firebase não encontrado")
        credential_source = credentials_path

    try:
        _firebase_app = firebase_admin.get_app()
    except ValueError:
        _firebase_app = firebase_admin.initialize_app(credentials.Certificate(credential_source))
    return _firebase_app


def send_fcm(device: NotificationDevice, payload: NotificationPayload) -> None:
    from firebase_admin import messaging

    app = get_firebase_app()
    message = messaging.Message(
        token=device.native_token,
        notification=messaging.Notification(title=payload.title, body=payload.body),
        data={
            "url": payload.url,
            "type": payload.notification_type,
            "tag": payload.tag or payload.notification_type,
        },
    )
    messaging.send(message, app=app)


async def send_to_user(
    db: AsyncSession,
    user_id: str,
    payload: NotificationPayload,
) -> tuple[int, int]:
    devices = list(
        (
            await db.scalars(
                select(NotificationDevice).where(
                    NotificationDevice.user_id == user_id,
                    NotificationDevice.is_active.is_(True),
                )
            )
        ).all()
    )
    sent = 0
    failed = 0
    for device in devices:
        try:
            if device.channel == "web_push":
                send_web_push(device, payload)
            elif device.channel == "fcm":
                send_fcm(device, payload)
            else:
                raise RuntimeError("Canal de notificação desconhecido")
        except ProviderConfigurationError as error:
            failed += 1
            logger.error("Provedor de notificação não configurado: %s", error)
        except Exception as error:
            failed += 1
            device.failure_count += 1
            if device.failure_count >= 3:
                device.is_active = False
            logger.warning("Falha ao notificar dispositivo %s: %s", device.id, error)
        else:
            sent += 1
            device.failure_count = 0
            device.last_success_at = utcnow()
        device.updated_at = utcnow()
    await db.commit()
    return sent, failed
