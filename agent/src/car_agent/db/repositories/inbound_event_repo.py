"""ProcessedResendEvent repository — idempotent inbound webhook deduplication."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from car_agent.db.database import async_session
from car_agent.db.models.inbound_event import ProcessedResendEvent


async def is_processed(event_id: str) -> bool:
    async with async_session() as session:
        row = await session.get(ProcessedResendEvent, event_id)
        return row is not None


async def mark_processed(event_id: str) -> bool:
    """Insert the event id. Returns False if already present (race condition)."""
    async with async_session() as session:
        try:
            session.add(ProcessedResendEvent(event_id=event_id))
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            return False
