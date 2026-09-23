"""Compose and send staff lifecycle emails (invites, password resets) — #248.

Links point at the dashboard (``AGROOS_BASE_URL``) and carry the one-time
token as a query parameter that ``AuthPage`` already understands
(``/login?invite=…`` and ``/login?reset=…``). Delivery goes through the
:class:`EmailProvider` port; when the configured adapter cannot deliver
(``EMAIL_PROVIDER=log``), the result says so and the link is in the log.
"""

from __future__ import annotations

from datetime import datetime

from app.config import get_settings
from app.services.providers.factory import get_email_provider


def _base_url() -> str:
    base = (get_settings().agroos_base_url or "").strip().rstrip("/")
    return base or "http://localhost:5173"


def invite_link(token: str) -> str:
    return f"{_base_url()}/login?invite={token}"


def reset_link(token: str) -> str:
    return f"{_base_url()}/login?reset={token}"


def send_invite_email(*, to: str, cooperative_name: str | None, role: str, token: str, expires_at: datetime) -> dict:
    org = cooperative_name or "your organisation"
    text = (
        f"You have been invited to join {org} on AgroOS as {role.replace('_', ' ')}.\n\n"
        f"Set your password and activate your account here:\n{invite_link(token)}\n\n"
        f"This link expires on {expires_at:%d %b %Y at %H:%M} UTC. "
        "If you were not expecting this invitation you can ignore this email."
    )
    result = get_email_provider().send(to=to, subject=f"You're invited to {org} on AgroOS", text=text)
    return {**result, "link": invite_link(token), "expires_at": expires_at}


def send_password_reset_email(*, to: str, token: str, expires_at: datetime) -> dict:
    text = (
        "Someone asked to reset the password for your AgroOS account.\n\n"
        f"Choose a new password here:\n{reset_link(token)}\n\n"
        f"This link expires on {expires_at:%d %b %Y at %H:%M} UTC. "
        "If you did not request a reset, no action is needed — your password is unchanged."
    )
    result = get_email_provider().send(to=to, subject="Reset your AgroOS password", text=text)
    return {**result, "link": reset_link(token), "expires_at": expires_at}
