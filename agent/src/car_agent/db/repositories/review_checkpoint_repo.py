"""ReviewCheckpoint repository — CRUD for HITL approval packets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from car_agent.db.database import async_session
from car_agent.db.models.review_checkpoint import ReviewCheckpoint


async def create_checkpoint(
    id: str,
    kind: str,
    customer_id: str,
    title: str,
    payload: dict[str, Any],
    search_result_id: str | None = None,
) -> ReviewCheckpoint:
    async with async_session() as session:
        row = ReviewCheckpoint(
            id=id,
            kind=kind,
            status="pending",
            search_result_id=search_result_id,
            customer_id=customer_id,
            title=title,
            payload=payload,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row


async def get_checkpoint(id: str) -> ReviewCheckpoint | None:
    async with async_session() as session:
        return await session.get(ReviewCheckpoint, id)


async def list_checkpoints(status: str | None = None) -> list[ReviewCheckpoint]:
    async with async_session() as session:
        stmt = select(ReviewCheckpoint).order_by(ReviewCheckpoint.created_at.desc())
        if status:
            stmt = stmt.where(ReviewCheckpoint.status == status)
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def replace_email_payload(
    id: str,
    email: dict[str, Any],
) -> ReviewCheckpoint | None:
    """Swap the `payload.email` block on a pending checkpoint (used by Retry)."""
    async with async_session() as session:
        row = await session.get(ReviewCheckpoint, id)
        if row is None:
            return None
        new_payload = dict(row.payload)
        new_payload["email"] = email
        row.payload = new_payload
        await session.commit()
        await session.refresh(row)
        return row


async def finalize_checkpoint(
    id: str,
    status: str,
    actor: str | None,
    result: dict[str, Any] | None,
) -> ReviewCheckpoint | None:
    """Move a pending checkpoint to a terminal status (approved/cancelled).

    Idempotency: returns None if the checkpoint isn't pending so the caller
    can surface a 409 to the client.
    """
    async with async_session() as session:
        row = await session.get(ReviewCheckpoint, id)
        if row is None:
            return None
        if row.status != "pending":
            return None
        row.status = status
        row.actor = actor
        row.result = result
        row.acted_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(row)
        return row
