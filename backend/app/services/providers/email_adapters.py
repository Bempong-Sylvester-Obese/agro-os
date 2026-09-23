"""Email adapters behind the :class:`EmailProvider` port (#248).

``LoggingEmailAdapter`` is the documented interim path: it writes the full
message (including the invite / reset link) to the application log so an
operator can forward it. ``SmtpEmailAdapter`` delivers through any SMTP relay
configured via ``SMTP_*`` settings. Swap providers in ``factory.py``.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings
from app.services.providers.base import EmailProvider

logger = logging.getLogger("agroos.email")


class LoggingEmailAdapter(EmailProvider):
    channel = "log"

    def send(self, *, to: str, subject: str, text: str) -> dict:
        logger.info("Staff email (not delivered — EMAIL_PROVIDER=log)\nTo: %s\nSubject: %s\n\n%s", to, subject, text)
        return {
            "delivered": False,
            "channel": self.channel,
            "message": "Email delivery is not configured; the link was written to the backend log.",
        }


class SmtpEmailAdapter(EmailProvider):
    channel = "smtp"

    def send(self, *, to: str, subject: str, text: str) -> dict:
        settings = get_settings()
        message = EmailMessage()
        message["From"] = settings.email_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(text)
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                if settings.smtp_use_tls:
                    smtp.starttls()
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            logger.error("SMTP delivery to %s failed: %s", to, exc)
            return {"delivered": False, "channel": self.channel, "message": f"Email delivery failed: {exc}"}
        return {"delivered": True, "channel": self.channel, "message": f"Email sent to {to}."}
