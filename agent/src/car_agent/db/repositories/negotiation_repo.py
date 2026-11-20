"""Negotiation repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from car_agent.db.models.negotiation import Negotiation as NegotiationORM
from car_agent.domain import Negotiation


async def create_negotiation(
    session: AsyncSession,
    negotiation_id: str,
    customer_id: int,
    listing_id: int,
) -> Negotiation:
    row = NegotiationORM(
        negotiation_id=negotiation_id,
        customer_id=customer_id,
        listing_id=listing_id,
        status="drafting",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return Negotiation.model_validate(row)


async def update_negotiation_status(
    session: AsyncSession, negotiation_id: str, status: str, **kwargs
) -> Negotiation | None:
    result = await session.execute(
        select(NegotiationORM).where(NegotiationORM.negotiation_id == negotiation_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        return None
    row.status = status
    for key, value in kwargs.items():
        if hasattr(row, key):
            setattr(row, key, value)
    await session.commit()
    await session.refresh(row)
    return Negotiation.model_validate(row)


async def get_negotiation_by_id(
    session: AsyncSession, negotiation_id: str
) -> Negotiation | None:
    result = await session.execute(
        select(NegotiationORM).where(NegotiationORM.negotiation_id == negotiation_id)
    )
    row = result.scalar_one_or_none()
    return Negotiation.model_validate(row) if row else None
