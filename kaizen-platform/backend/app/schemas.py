from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class NamedRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Informe um nome válido")
        return cleaned


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str | None
    phone: str | None
    auth_provider: str
    is_verified: bool


class RegisterRequest(NamedRequest):
    email: EmailStr
    password: str = Field(min_length=12, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class PhoneCodeRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=30)
    name: str | None = Field(default=None, min_length=2, max_length=80)

    @field_validator("name")
    @classmethod
    def clean_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Informe um nome válido")
        return cleaned


class PhoneCodeVerifyRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=30)
    code: str = Field(pattern=r"^\d{6}$")


class CodeConfirmRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class RecoveryRequest(BaseModel):
    channel: Literal["email", "phone"]
    identifier: str = Field(min_length=3, max_length=320)


class RecoveryConfirmRequest(BaseModel):
    channel: Literal["email", "phone"]
    identifier: str = Field(min_length=3, max_length=320)
    code: str = Field(pattern=r"^\d{6}$")
    new_password: str | None = Field(default=None, min_length=12, max_length=200)


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserOut


class GoogleOAuthStartOut(BaseModel):
    authorization_url: str


class GoogleOAuthExchangeRequest(BaseModel):
    code: str = Field(min_length=32, max_length=512)


class MessageResponse(BaseModel):
    message: str
    debug_code: str | None = None
