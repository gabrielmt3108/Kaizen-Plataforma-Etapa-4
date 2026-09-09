import asyncio
import logging
import smtplib
from email.message import EmailMessage

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger("kaizen.delivery")


def _email_from_address() -> str:
    return settings.email_from_email or settings.smtp_from_email


def _email_from_name() -> str:
    return settings.email_from_name or settings.smtp_from_name


def _recovery_message(code: str) -> str:
    return (
        f"Seu código de verificação do Kaizen Life é {code}. "
        f"Ele expira em {settings.recovery_code_minutes} minutos.\n\n"
        "Se você não solicitou este código, ignore esta mensagem."
    )


def _send_smtp(destination: str, code: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Seu código do Kaizen Life"
    message["From"] = f"{_email_from_name()} <{_email_from_address()}>"
    message["To"] = destination
    message.set_content(_recovery_message(code))
    smtp_class = smtplib.SMTP_SSL if settings.smtp_security == "ssl" else smtplib.SMTP
    with smtp_class(settings.smtp_host, settings.smtp_port, timeout=15) as client:
        if settings.smtp_security == "starttls":
            client.starttls()
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)


async def _send_brevo(destination: str, code: str) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            settings.brevo_api_url,
            headers={
                "accept": "application/json",
                "api-key": settings.brevo_api_key,
                "content-type": "application/json",
            },
            json={
                "sender": {
                    "name": _email_from_name(),
                    "email": _email_from_address(),
                },
                "to": [{"email": destination}],
                "subject": "Seu código do Kaizen Life",
                "textContent": _recovery_message(code),
            },
        )
    response.raise_for_status()


async def _send_twilio(destination: str, code: str) -> None:
    url = (
        "https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.twilio_account_sid}/Messages.json"
    )
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            url,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            data={
                "To": destination,
                "From": settings.twilio_from_phone,
                "Body": (
                    f"Kaizen Life: seu código é {code}. "
                    f"Expira em {settings.recovery_code_minutes} minutos."
                ),
            },
        )
    response.raise_for_status()


async def deliver_code(channel: str, destination: str, code: str) -> None:
    mode = settings.email_delivery_mode if channel == "email" else settings.sms_delivery_mode
    if mode == "console" and settings.environment != "production":
        logger.warning("Código local de %s para %s: %s", channel, destination, code)
        return
    try:
        if channel == "email" and mode == "smtp":
            await asyncio.to_thread(_send_smtp, destination, code)
            return
        if channel == "email" and mode == "brevo":
            await _send_brevo(destination, code)
            return
        if channel == "phone" and mode == "twilio":
            await _send_twilio(destination, code)
            return
    except (OSError, smtplib.SMTPException, httpx.HTTPError):
        logger.exception("Falha no provedor de entrega de código (%s)", channel)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível enviar o código agora. Tente novamente em instantes.",
        ) from None
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="O provedor deste canal ainda não foi configurado.",
    )
