"""Customer repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from car_agent.db.database import async_session
from car_agent.db.models.customer import Customer as CustomerORM
from car_agent.domain import Customer


async def create_customer(
    session: AsyncSession, name: str | None, email: str, phone: str | None = None
) -> Customer:
    row = CustomerORM(name=name, email=email, phone=phone)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return Customer.model_validate(row)


async def get_customer(session: AsyncSession, customer_id: str) -> Customer | None:
    row = await session.get(CustomerORM, customer_id)
    return Customer.model_validate(row) if row else None


async def get_customer_by_email(email: str) -> Customer | None:
    async with async_session() as session:
        stmt = select(CustomerORM).where(CustomerORM.email == email)
        row = (await session.execute(stmt)).scalar_one_or_none()
        return Customer.model_validate(row) if row else None


async def set_customer_contact(
    customer_id: str, name: str | None = None, phone: str | None = None
) -> Customer | None:
    """Record the contact details a customer gave us at order time.

    Latest submission wins: a customer who corrects their name or phone on a
    second order should not keep the stale value. Passing None leaves a field
    untouched rather than clearing it."""
    async with async_session() as session:
        row = await session.get(CustomerORM, customer_id)
        if row is None:
            return None
        if name is not None:
            row.name = name
        if phone is not None:
            row.phone = phone
        await session.commit()
        await session.refresh(row)
        return Customer.model_validate(row)


async def get_or_create_customer(email: str, name: str | None = None) -> Customer:
    """Find a customer by email or create a stub. Used by anonymous flows
    (analyze, negotiate-for-me) so every persisted entity has a customer_id FK."""
    async with async_session() as session:
        stmt = select(CustomerORM).where(CustomerORM.email == email)
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = CustomerORM(email=email, name=name)
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return Customer.model_validate(row)
