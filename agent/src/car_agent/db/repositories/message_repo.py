"""Message repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from car_agent.db.models.negotiation import Message as MessageORM
from car_agent.domain import NegotiationDirection, NegotiationRound


async def create_message(
    session: AsyncSession,
    negotiation_db_id: int,
    direction: NegotiationDirection,
    body: str,
    subject: str | None = None,
    sendgrid_message_id: str | None = None,
) -> NegotiationRound:
    row = MessageORM(
        negotiation_id=negotiation_db_id,
        direction=direction,
        subject=subject,
        body=body,
        sendgrid_message_id=sendgrid_message_id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _message_to_round(row, round_number=1)


async def get_messages_for_negotiation(
    session: AsyncSession, negotiation_db_id: int
) -> list[NegotiationRound]:
    """Return all messages for a negotiation as ordered rounds."""
    result = await session.execute(
        select(MessageORM)
        .where(MessageORM.negotiation_id == negotiation_db_id)
        .order_by(MessageORM.timestamp.asc())
    )
    rows = list(result.scalars().all())
    return [_message_to_round(row, round_number=i + 1) for i, row in enumerate(rows)]


def _message_to_round(row: MessageORM, round_number: int) -> NegotiationRound:
    return NegotiationRound(
        round_number=round_number,
        direction=row.direction,  # type: ignore[arg-type]
        subject=row.subject,
        body=row.body,
        timestamp=row.timestamp,
    )
