from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.database_urls import normalize_async_database_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="KAIZEN_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Kaizen Life API"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite+aiosqlite:///./kaizen.db"
    database_pool_size: int = 5
    database_max_overflow: int = 5
    jwt_secret: str = "development-only-change-this-secret-before-production-0123456789"
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    recovery_code_minutes: int = 10
    refresh_cookie_name: str = "kaizen_refresh"
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"
    auto_create_tables: bool = True
    email_delivery_mode: Literal["console", "smtp", "brevo", "disabled"] = "console"
    sms_delivery_mode: Literal["console", "twilio", "disabled"] = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Kaizen Life"
    smtp_security: Literal["starttls", "ssl", "none"] = "starttls"
    brevo_api_key: str = ""
    brevo_api_url: str = "https://api.brevo.com/v3/smtp/email"
    email_from_email: str = ""
    email_from_name: str = "Kaizen Life"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_phone: str = ""
    google_oauth_enabled: bool = False
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    oauth_return_origins: str = (
        "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8080,"
        "capacitor://localhost,"
        "com.kaizenlife.app://oauth"
    )
    oauth_attempt_minutes: int = 10
    oauth_exchange_minutes: int = 2
    web_push_enabled: bool = False
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:contato@seu-dominio.com"
    firebase_credentials_path: str = ""
    firebase_credentials_json: str = ""
    notification_cron_enabled: bool = False
    cron_secret: str = ""
    notification_worker_interval_seconds: int = 30

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> str:
        return normalize_async_database_url(str(value))

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def oauth_return_origin_list(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.oauth_return_origins.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.environment == "production":
            weak_markers = ("change-this", "troque-por", "development-only")
            if len(self.jwt_secret) < 64 or any(
                marker in self.jwt_secret.lower() for marker in weak_markers
            ):
                raise ValueError("KAIZEN_JWT_SECRET precisa ter ao menos 64 caracteres aleatórios")
            if not self.cookie_secure:
                raise ValueError("KAIZEN_COOKIE_SECURE precisa ser true em produção")
            if self.debug:
                raise ValueError("KAIZEN_DEBUG precisa ser false em produção")
            if "console" in {self.email_delivery_mode, self.sms_delivery_mode}:
                raise ValueError("Os modos de entrega console não podem ser usados em produção")
            if self.auto_create_tables:
                raise ValueError("Use migrações e KAIZEN_AUTO_CREATE_TABLES=false em produção")
            if self.web_push_enabled and (
                not self.vapid_public_key
                or not self.vapid_private_key
                or not self.vapid_subject.startswith(("mailto:", "https://"))
            ):
                raise ValueError("Configure as chaves VAPID e um assunto válido para Web Push")
            if self.notification_cron_enabled and len(self.cron_secret) < 32:
                raise ValueError(
                    "KAIZEN_CRON_SECRET precisa ter ao menos 32 caracteres aleatórios"
                )
        if self.email_delivery_mode == "smtp" and not all(
            (self.smtp_host, self.smtp_from_email or self.email_from_email)
        ):
            raise ValueError("Configure KAIZEN_SMTP_HOST e KAIZEN_SMTP_FROM_EMAIL")
        if self.email_delivery_mode == "brevo" and not all(
            (self.brevo_api_key, self.email_from_email)
        ):
            raise ValueError("Configure KAIZEN_BREVO_API_KEY e KAIZEN_EMAIL_FROM_EMAIL")
        if self.sms_delivery_mode == "twilio" and not all(
            (self.twilio_account_sid, self.twilio_auth_token, self.twilio_from_phone)
        ):
            raise ValueError("Configure as credenciais e o número remetente da Twilio")
        if self.google_oauth_enabled and not all(
            (self.google_client_id, self.google_client_secret, self.google_redirect_uri)
        ):
            raise ValueError("Configure cliente, segredo e callback do Google OAuth")
        if (
            self.environment == "production"
            and self.google_oauth_enabled
            and not self.google_redirect_uri.startswith("https://")
        ):
            raise ValueError("O callback do Google OAuth precisa usar HTTPS em produção")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
