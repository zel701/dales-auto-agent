"""FastAPI auth dependencies — read the customer-session cookie."""

from __future__ import annotations

from fastapi import HTTPException, Request

from car_agent.db.models.customer import Customer as CustomerORM
from car_agent.db.repositories.session_repo import get_customer_for_token

COOKIE_NAME = "cs_token"


async def get_optional_customer(request: Request) -> CustomerORM | None:
    """Resolve the cookie to a Customer ORM row, or None if no/invalid session."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return await get_customer_for_token(token)


async def require_customer(request: Request) -> CustomerORM:
    customer = await get_optional_customer(request)
    if customer is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return customer
