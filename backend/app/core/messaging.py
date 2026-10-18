"""Outgoing email/SMS seam. Swap the bodies for a provider (SES, Postmark, MSG91…) without touching callers."""
import logging
import smtplib
from email.message import EmailMessage

from .config import settings

log = logging.getLogger("qutncandy.messaging")


def send_email(to: str, subject: str, body: str) -> None:
    """Send a plain-text email. Never raises: a failed email must not break an order."""
    if not settings.smtp_host:
        log.warning("Email (SMTP not configured) to=%s subject=%s\n%s", to, subject, body)
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.mail_from, to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except Exception:  # noqa: BLE001
        log.exception("Failed to send email to %s", to)


def send_sms(phone: str, text: str) -> None:
    """Placeholder until an SMS provider is chosen (needed for phone OTP)."""
    log.warning("SMS (no provider configured) to=%s: %s", phone, text)
