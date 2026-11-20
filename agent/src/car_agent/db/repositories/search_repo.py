"""Search repository."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from car_agent.db.models.search import Search as SearchORM


async def create_search(
    session: AsyncSession,
    customer_id: int,
    params: dict,
    num_found: int = 0,
) -> int:
    """Persist a search and return its DB id."""
    row = SearchORM(customer_id=customer_id, params_json=params, num_found=num_found)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row.id
