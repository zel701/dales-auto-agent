"""SearchResult repository — cached search results for email CTA links."""

from __future__ import annotations

from typing import Any

from car_agent.db.database import async_session
from car_agent.db.models.search_result import SearchResult


async def create_search_result(
    uuid: str,
    customer_id: str,
    car_info: dict[str, Any],
    listings: list[dict[str, Any]],
    num_found: int,
) -> None:
    async with async_session() as session:
        session.add(SearchResult(
            uuid=uuid,
            customer_id=customer_id,
            car_info=car_info,
            listings=listings,
            num_found=num_found,
        ))
        await session.commit()


async def get_search_result(uuid: str) -> SearchResult | None:
    async with async_session() as session:
        return await session.get(SearchResult, uuid)


async def mark_search_result_completed(uuid: str) -> None:
    """Flip status to 'completed' so the results page rejects further visits."""
    async with async_session() as session:
        row = await session.get(SearchResult, uuid)
        if row is None:
            return
        row.status = "completed"
        await session.commit()
