"""Resend Inbound helpers: webhook signature verification and email body fetch."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

RESEND_WEBHOOK_SECRET = os.environ.get("RESEND_WEBHOOK_SECRET", "")


def verify_webhook(payload: bytes, headers: dict[str, str]) -> bool:
    """Verify a Resend inbound webhook signature using Svix (which Resend uses internally).

    Returns True if the signature is valid. Always returns True when
    RESEND_WEBHOOK_SECRET is not configured (dev/test convenience).
    """
    if not RESEND_WEBHOOK_SECRET:
        logger.warning("RESEND_WEBHOOK_SECRET not set; skipping signature verification")
        return True

    try:
        from svix.webhooks import Webhook

        wh = Webhook(RESEND_WEBHOOK_SECRET)
        wh.verify(payload, headers)
        return True
    except Exception as exc:
        logger.warning(
            "Webhook signature verification failed: %s | svix-id=%s svix-timestamp=%s",
            exc,
            headers.get("svix-id", "MISSING"),
            headers.get("svix-timestamp", "MISSING"),
        )
        return False


async def fetch_email_body(email_id: str) -> str:
    """Fetch the plain-text body of a received email from the Resend API.

    Falls back to the HTML body (stripped of tags) if text is empty.
    Returns an empty string on error.
    """
    try:
        import resend

        resend.api_key = os.environ.get("RESEND_API_KEY", "")
        received = resend.Emails.Receiving.get(email_id=email_id)

        text = received.get("text") or ""
        if text.strip():
            return text.strip()

        html = received.get("html") or ""
        return _strip_html(html).strip()
    except Exception:
        logger.exception("Failed to fetch email body for %s", email_id)
        return ""


def _strip_html(html: str) -> str:
    """Very light HTML tag stripper — good enough for dealer reply bodies."""
    import re

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\s+", " ", text)
    return text
