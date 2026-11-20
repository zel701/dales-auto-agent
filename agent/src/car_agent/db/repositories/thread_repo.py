"""NegotiationThread repository — maps negotiation_id to LangGraph thread_id."""

from __future__ import annotations

import logging

from car_agent.db.database import async_session
from car_agent.db.models.negotiation import NegotiationThread

logger = logging.getLogger(__name__)


async def register_negotiation(negotiation_id: str, thread_id: str) -> None:
    """Store a negotiation_id -> thread_id mapping in the database."""
    async with async_session() as session:
        session.add(NegotiationThread(
            negotiation_id=negotiation_id,
            thread_id=thread_id,
        ))
        await session.commit()
    logger.info("Registered negotiation %s -> thread %s", negotiation_id, thread_id)


async def get_thread_id(negotiation_id: str) -> str | None:
    """Look up the thread_id for a negotiation from the database."""
    async with async_session() as session:
        row = await session.get(NegotiationThread, negotiation_id)
    return row.thread_id if row else None
