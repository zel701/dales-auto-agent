"""Require a successful delivery before completing an email approval."""

from collections.abc import Awaitable

from car_agent.clients.email import EmailResult


class EmailDeliveryFailed(Exception):
    """The provider rejected the send and the approval can be retried."""


async def require_delivery(send: Awaitable[EmailResult]) -> EmailResult:
    result = await send
    if not result.success:
        raise EmailDeliveryFailed(f"Email send failed: {result.error or 'Unknown error'}")
    return result
