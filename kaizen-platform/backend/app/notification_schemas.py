from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NotificationPreferenceUpdate(BaseModel):
    enabled: bool | None = None
    habit_reminders: bool | None = None
    task_reminders: bool | None = None
    motivational: bool | None = None
    goal_alerts: bool | None = None
    coach_notifications: bool | None = None
    timezone: str | None = Field(default=None, min_length=3, max_length=64)
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None


class NotificationPreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enabled: bool
    habit_reminders: bool
    task_reminders: bool
    motivational: bool
    goal_alerts: bool
    coach_notifications: bool
    timezone: str
    quiet_hours_start: time
    quiet_hours_end: time


class NotificationDeviceRequest(BaseModel):
    channel: Literal["web_push", "fcm"]
    endpoint: str | None = Field(default=None, max_length=2048)
    p256dh: str | None = Field(default=None, max_length=180)
    auth: str | None = Field(default=None, max_length=180)
    native_token: str | None = Field(default=None, max_length=512)
    platform: Literal["web", "android", "ios"] = "web"
    device_name: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_channel_fields(self) -> "NotificationDeviceRequest":
        if self.channel == "web_push" and not (self.endpoint and self.p256dh and self.auth):
            raise ValueError("Web Push exige endpoint, p256dh e auth")
        if self.channel == "fcm" and not self.native_token:
            raise ValueError("FCM exige o token nativo do dispositivo")
        return self


class NotificationDeviceRemove(BaseModel):
    channel: Literal["web_push", "fcm"]
    endpoint: str | None = Field(default=None, max_length=2048)
    native_token: str | None = Field(default=None, max_length=512)


class NotificationDeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel: str
    platform: str
    device_name: str | None
    is_active: bool
    created_at: datetime


class NotificationStatusOut(BaseModel):
    server_enabled: bool
    web_push_enabled: bool
    native_push_enabled: bool
    vapid_public_key: str | None
    devices: list[NotificationDeviceOut]
    preferences: NotificationPreferenceOut


class NotificationPayload(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=320)
    url: str = Field(default="/", max_length=500)
    notification_type: str = Field(default="general", min_length=1, max_length=40)
    tag: str | None = Field(default=None, max_length=120)


class NotificationSendOut(BaseModel):
    sent_devices: int
    failed_devices: int
    message: str
