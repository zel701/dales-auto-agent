"""Order repository — customer negotiation requests with metadata."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from car_agent.db.database import async_session
from car_agent.db.models.order import Order


async def create_order(
    uuid: str,
    search_result_id: str,
    customer_id: str,
    car_info: dict[str, Any],
    selected_listings: list[dict[str, Any]],
    need_by_date: datetime,
    payment_method: str,
    delivery_method: str,
    credit_score_range: str | None = None,
) -> None:
    async with async_session() as session:
        session.add(Order(
            uuid=uuid,
            search_result_id=search_result_id,
            customer_id=customer_id,
            car_info=car_info,
            selected_listings=selected_listings,
            need_by_date=need_by_date,
            payment_method=payment_method,
            credit_score_range=credit_score_range,
            delivery_method=delivery_method,
        ))
        await session.commit()
