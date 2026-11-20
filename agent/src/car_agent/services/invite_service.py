"""Invitation code service — unlock and consume semantics for the beta gate.

Two distinct checks, deliberately asymmetric:
  * unlocking (viewing the site) tolerates an already-consumed code
  * consuming (submitting an analysis) does not
"""

from __future__ import annotations

import logging

from car_agent.db.repositories.invite_repo import (
    attribute_invite_code,
    consume_invite_code,
    get_invite_by_code,
    mark_unlocked,
    normalize_code,
    release_invite_code,
)

logger = logging.getLogger(__name__)


class InviteError(Exception):
    """Base for invite failures. `reason` is a stable machine-readable tag."""

    reason = "invalid"
    message = "Invalid invitation code."


class InvalidInviteError(InviteError):
    reason = "invalid"
    message = "Invalid invitation code."


class ConsumedInviteError(InviteError):
    reason = "consumed"
    message = "This invitation code has already been used."


async def redeem_for_unlock(raw: str) -> str | None:
    """Validate a code for viewing access. Returns the canonical code or None."""
    code = normalize_code(raw)
    if code is None:
        return None
    row = await mark_unlocked(code)
    if row is None:
        return None
    logger.info(
        "Invite unlocked", extra={"label": row.label, "unlock_count": row.unlock_count}
    )
    return code


async def assert_submittable(raw: str) -> str:
    """Validate a code for spending. Returns the canonical code or raises.

    Called before any expensive work so an invalid code never costs a
    MarketCheck search or an LLM call.
    """
    code = normalize_code(raw)
    if code is None:
        raise InvalidInviteError()
    row = await get_invite_by_code(code)
    if row is None or row.revoked_at is not None:
        raise InvalidInviteError()
    if row.consumed_at is not None:
        raise ConsumedInviteError()
    return code


async def consume(code: str) -> bool:
    """Spend the code up front, before the work it pays for runs.

    Claiming it here rather than after the analysis is what makes a second
    submit fail fast: the analysis takes 10-30s, and two requests inside that
    window would otherwise both pass validation.
    """
    ok = await consume_invite_code(code)
    if ok:
        logger.info("Invite consumed")
    return ok


async def attribute(code: str, customer_id: str, search_result_id: str) -> None:
    """Record who spent the code, once the analysis has produced them."""
    await attribute_invite_code(code, customer_id, search_result_id)
    logger.info(
        "Invite attributed",
        extra={"customer_id": customer_id, "search_result_id": search_result_id},
    )


async def release(code: str) -> None:
    """Give the code back after the work it paid for failed."""
    await release_invite_code(code)
    logger.warning("Invite released after a failed analysis")
