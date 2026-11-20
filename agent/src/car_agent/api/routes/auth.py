"""Auth routes — passwordless 6-digit OTP login."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from car_agent.api.auth import COOKIE_NAME, get_optional_customer
from car_agent.api.schemas.auth import (
    CustomerSummary,
    LogoutResponse,
    MeResponse,
    RequestOtpRequest,
    RequestOtpResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from car_agent.clients.email import send_email
from car_agent.db.repositories.customer_repo import get_or_create_customer
from car_agent.db.repositories.otp_repo import (
    MAX_ACTIVE_PER_EMAIL,
    consume_otp,
    count_active_otps,
    create_otp,
)
from car_agent.db.repositories.session_repo import create_session, revoke_session
from car_agent.services.email_templates import build_otp_email

logger = logging.getLogger(__name__)

router = APIRouter()


def _cookie_kwargs() -> dict:
    secure = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
    days = int(os.environ.get("SESSION_TTL_DAYS", "30"))
    return {
        "httponly": True,
        "secure": secure,
        "samesite": "lax",
        "path": "/",
        "max_age": days * 24 * 60 * 60,
    }


@router.post("/api/auth/request-otp", response_model=RequestOtpResponse)
async def request_otp(req: RequestOtpRequest) -> RequestOtpResponse:
    """Generate and email a 6-digit code. Always returns 200 to avoid leaking
    whether an email is registered."""
    email = req.email.lower().strip()
    active = await count_active_otps(email)
    if active >= MAX_ACTIVE_PER_EMAIL:
        logger.info("OTP throttled for %s (%d active)", email, active)
        return RequestOtpResponse(ok=True)

    code = await create_otp(email)
    payload = build_otp_email(code)
    result = await send_email(
        to_email=email,
        subject=payload["subject"],
        body=payload["full_html"],
        html=True,
    )
    if not result.success:
        logger.error("OTP email failed for %s: %s", email, result.error)
    return RequestOtpResponse(ok=True)


@router.post("/api/auth/verify-otp", response_model=VerifyOtpResponse)
async def verify_otp(req: VerifyOtpRequest, response: Response) -> VerifyOtpResponse:
    """Validate the code, get-or-create the customer, mint a session cookie."""
    email = req.email.lower().strip()
    ok = await consume_otp(email, req.code)
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid or expired code")

    customer = await get_or_create_customer(email)
    token = await create_session(customer.id)
    response.set_cookie(COOKIE_NAME, token, **_cookie_kwargs())
    return VerifyOtpResponse(
        customer=CustomerSummary(id=customer.id, email=customer.email)
    )


@router.post("/api/auth/logout", response_model=LogoutResponse)
async def logout(request: Request, response: Response) -> LogoutResponse:
    """Revoke the session row and clear the cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        await revoke_session(token)
    response.delete_cookie(COOKIE_NAME, path="/")
    return LogoutResponse(ok=True)


@router.get("/api/auth/me", response_model=MeResponse)
async def me(customer=Depends(get_optional_customer)) -> MeResponse:
    if customer is None:
        return MeResponse(customer=None)
    return MeResponse(
        customer=CustomerSummary(id=customer.id, email=customer.email)
    )
