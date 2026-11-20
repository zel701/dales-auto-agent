"""POST /api/invites/redeem — exchange an invitation code for site access.

Rate limiting matters more than usual here: codes are only `DALE-XXXX` (30^4 =
810,000 combinations), so with ~100 live codes a blind guess lands roughly 1 in
8,100. Two sliding windows guard the endpoint, both counting *failures* only:

  * per-IP    — stops one impatient guesser
  * global    — stops a distributed one, which per-IP limiting cannot see

Both windows are process-local. If the agent is ever scaled past a single
instance these need to move to Redis, otherwise the effective limit multiplies
by the instance count.
"""

from __future__ import annotations

import logging
import os
import time

from fastapi import APIRouter, HTTPException, Request

from car_agent.api.schemas import RedeemInviteRequest, RedeemInviteResponse
from car_agent.services.invite_service import redeem_for_unlock

logger = logging.getLogger(__name__)

router = APIRouter()


def _int_env(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


_ip_failures: dict[str, list[float]] = {}
_global_failures: list[float] = []


def _client_ip(request: Request) -> str:
    """The browser's IP, not the website's.

    The website proxies these calls, so `request.client.host` is the Next
    server. The real client arrives in X-Forwarded-For, first hop.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _prune(times: list[float], window_seconds: int, now: float) -> list[float]:
    return [t for t in times if now - t < window_seconds]


def _check_rate_limits(ip: str) -> None:
    """Raise 429 if this IP, or everyone collectively, has failed too often."""
    now = time.monotonic()

    ip_window = _int_env("INVITE_RATE_LIMIT_WINDOW_MIN", 15) * 60
    ip_max = _int_env("INVITE_RATE_LIMIT_MAX", 10)
    recent = _prune(_ip_failures.get(ip, []), ip_window, now)
    _ip_failures[ip] = recent
    if len(recent) >= ip_max:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please wait a few minutes and try again.",
        )

    global_window = _int_env("INVITE_GLOBAL_LIMIT_WINDOW_MIN", 60) * 60
    global_max = _int_env("INVITE_GLOBAL_LIMIT_MAX", 60)
    _global_failures[:] = _prune(_global_failures, global_window, now)
    if len(_global_failures) >= global_max:
        logger.error(
            "Invite redemption globally rate-limited — likely code enumeration",
            extra={"failures": len(_global_failures), "window_seconds": global_window},
        )
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please wait a few minutes and try again.",
        )


def _record_failure(ip: str) -> None:
    now = time.monotonic()
    _ip_failures.setdefault(ip, []).append(now)
    _global_failures.append(now)
    # Bound memory: drop IPs whose entries have all aged out.
    if len(_ip_failures) > 10_000:
        window = _int_env("INVITE_RATE_LIMIT_WINDOW_MIN", 15) * 60
        for key in [k for k, v in _ip_failures.items() if not _prune(v, window, now)]:
            del _ip_failures[key]


@router.post("/api/invites/redeem", response_model=RedeemInviteResponse)
async def redeem_invite(
    req: RedeemInviteRequest, request: Request
) -> RedeemInviteResponse:
    ip = _client_ip(request)
    _check_rate_limits(ip)

    code = await redeem_for_unlock(req.code)
    if code is None:
        _record_failure(ip)
        logger.info("Invite redemption failed", extra={"client_ip": ip})
        raise HTTPException(status_code=401, detail="Invalid invitation code.")

    return RedeemInviteResponse(ok=True, code=code)
