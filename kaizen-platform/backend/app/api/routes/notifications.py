import hashlib
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.config import settings
from app.dependencies import CurrentUser, Database
from app.models import NotificationDevice, NotificationPreference
from app.notification_schemas import (
    NotificationDeviceOut,
    NotificationDeviceRemove,
    NotificationDeviceRequest,
    NotificationPayload,
    NotificationPreferenceOut,
    NotificationPreferenceUpdate,
    NotificationSendOut,
    NotificationStatusOut,
)
from app.services.notifications import send_to_user

router = APIRouter(prefix="/notifications", tags=["notificações"])


def native_push_configured() -> bool:
    return bool(settings.firebase_credentials_path or settings.firebase_credentials_json)


async def get_preferences(db: Database, user_id: str) -> NotificationPreference:
    preferences = await db.scalar(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    if not preferences:
        preferences = NotificationPreference(user_id=user_id)
        db.add(preferences)
        await db.commit()
        await db.refresh(preferences)
    return preferences


def device_key(payload: NotificationDeviceRequest | NotificationDeviceRemove) -> str:
    value = payload.endpoint if payload.channel == "web_push" else payload.native_token
    if not value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Identificador do dispositivo ausente.",
        )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@router.get("/status", response_model=NotificationStatusOut)
async def notification_status(db: Database, user: CurrentUser) -> NotificationStatusOut:
    preferences = await get_preferences(db, user.id)
    devices = list(
        (
            await db.scalars(
                select(NotificationDevice)
                .where(
                    NotificationDevice.user_id == user.id,
                    NotificationDevice.is_active.is_(True),
                )
                .order_by(NotificationDevice.created_at.desc())
            )
        ).all()
    )
    return NotificationStatusOut(
        server_enabled=settings.web_push_enabled or native_push_configured(),
        web_push_enabled=settings.web_push_enabled,
        native_push_enabled=native_push_configured(),
        vapid_public_key=settings.vapid_public_key if settings.web_push_enabled else None,
        devices=[NotificationDeviceOut.model_validate(item) for item in devices],
        preferences=NotificationPreferenceOut.model_validate(preferences),
    )


@router.put("/preferences", response_model=NotificationPreferenceOut)
async def update_preferences(
    payload: NotificationPreferenceUpdate,
    db: Database,
    user: CurrentUser,
) -> NotificationPreference:
    preferences = await get_preferences(db, user.id)
    data = {
        key: value
        for key, value in payload.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if data.get("timezone"):
        try:
            ZoneInfo(data["timezone"])
        except ZoneInfoNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Fuso horário desconhecido.",
            ) from error
    for key, value in data.items():
        setattr(preferences, key, value)
    await db.commit()
    await db.refresh(preferences)
    return preferences


@router.post("/devices", response_model=NotificationDeviceOut)
async def register_device(
    payload: NotificationDeviceRequest,
    request: Request,
    db: Database,
    user: CurrentUser,
) -> NotificationDevice:
    if payload.channel == "web_push" and not settings.web_push_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web Push ainda não foi configurado no servidor.",
        )
    if payload.channel == "fcm" and not native_push_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notificações nativas ainda não foram configuradas no servidor.",
        )
    key = device_key(payload)
    device = await db.scalar(
        select(NotificationDevice).where(NotificationDevice.device_key == key)
    )
    values = payload.model_dump()
    if device:
        device.user_id = user.id
        for field, value in values.items():
            if field != "channel":
                setattr(device, field, value)
        device.channel = payload.channel
        device.is_active = True
        device.failure_count = 0
    else:
        device = NotificationDevice(
            user_id=user.id,
            device_key=key,
            **values,
        )
        db.add(device)
    device.user_agent = (request.headers.get("user-agent") or "")[:300] or None
    await db.commit()
    await db.refresh(device)
    return device


@router.post("/devices/remove", status_code=status.HTTP_204_NO_CONTENT)
async def remove_device(
    payload: NotificationDeviceRemove,
    db: Database,
    user: CurrentUser,
) -> None:
    key = device_key(payload)
    device = await db.scalar(
        select(NotificationDevice).where(
            NotificationDevice.user_id == user.id,
            NotificationDevice.device_key == key,
        )
    )
    if device:
        device.is_active = False
        await db.commit()


@router.post("/test", response_model=NotificationSendOut)
async def send_test_notification(db: Database, user: CurrentUser) -> NotificationSendOut:
    preferences = await get_preferences(db, user.id)
    if not preferences.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="As notificações estão desativadas nas preferências da conta.",
        )
    sent, failed = await send_to_user(
        db,
        user.id,
        NotificationPayload(
            title="Kaizen Life está conectado",
            body="As notificações deste dispositivo estão funcionando certinho.",
            url="/?page=settings",
            notification_type="test",
            tag="kaizen-test",
        ),
    )
    return NotificationSendOut(
        sent_devices=sent,
        failed_devices=failed,
        message=(
            "Notificação enviada."
            if sent
            else "Nenhum dispositivo configurado conseguiu receber a notificação."
        ),
    )
