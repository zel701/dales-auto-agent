"""Resend email client with dry-run support."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DRY_RUN = os.environ.get("DRY_RUN", "true").lower() == "true"
DEV_EMAIL_OVERRIDE = os.environ.get("DEV_EMAIL_OVERRIDE", "")


@dataclass
class EmailResult:
    success: bool
    message_id: str | None
    dry_run: bool
    error: str | None = None


async def send_email(
    to_email: str,
    subject: str,
    body: str,
    negotiation_id: str | None = None,
    html: bool = False,
    in_reply_to: str | None = None,
    references: list[str] | None = None,
) -> EmailResult:
    """Send an email via Resend, or log it if DRY_RUN is enabled.

    Uses a unique reply-to address (deals+{negotiation_id}@domain) so
    inbound replies can be routed back to the correct negotiation thread.

    Pass in_reply_to (the Message-ID of the email being replied to) and
    references (all prior Message-IDs in the thread) so mail clients group
    the message into the existing thread.
    """
    from_email = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")
    reply_to_domain = os.environ.get("REPLY_TO_DOMAIN", "yourdomain.com")

    if negotiation_id:
        reply_to = f"deals+{negotiation_id}@{reply_to_domain}"
    else:
        reply_to = from_email

    headers: dict[str, str] = {}
    if in_reply_to:
        headers["In-Reply-To"] = in_reply_to
    if references:
        headers["References"] = " ".join(references)

    if DEV_EMAIL_OVERRIDE and negotiation_id:
        # Keep the subject intact so threading works in dev; record the real
        # recipient in a header instead.
        headers["X-Original-To"] = to_email
        to_email = DEV_EMAIL_OVERRIDE

    if DRY_RUN:
        logger.info(
            "[DRY RUN] Email NOT sent | To: %s | Subject: %s | In-Reply-To: %s",
            to_email, subject, in_reply_to or "-",
        )
        return EmailResult(success=True, message_id="dry-run", dry_run=True)

    try:
        import resend

        resend.api_key = os.environ.get("RESEND_API_KEY", "")

        params: resend.Emails.SendParams = {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "reply_to": reply_to,
        }
        if headers:
            params["headers"] = headers
        if html:
            params["html"] = body
        else:
            params["text"] = body

        response = resend.Emails.send(params)
        return EmailResult(
            success=True,
            message_id=response.get("id"),
            dry_run=False,
        )
    except Exception as e:
        logger.error("Email send failed: %s", e)
        return EmailResult(success=False, message_id=None, dry_run=False, error=str(e))
