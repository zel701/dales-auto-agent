"""Start and manage per-dealership negotiation graph threads.

Called from POST /api/negotiate after the Order is created.
Each selected dealership gets its own LangGraph thread (thread_id = negotiation_id).
"""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from car_agent.db.database import async_session
from car_agent.db.models.order import Order
from car_agent.db.repositories.thread_repo import get_thread_id, register_negotiation
from car_agent.logging_config import neg_id_var
from car_agent.state import CustomerCtx, DealershipGroup, NegotiationState

logger = logging.getLogger(__name__)


def _dealer_key(listing: dict) -> str:
    """Normalize dealer name for grouping."""
    return (listing.get("dealer_name") or "").strip().lower()


def _group_by_dealership(listings: list[dict]) -> list[DealershipGroup]:
    """Group selected listings by dealership, one group per unique dealer."""
    groups: dict[str, DealershipGroup] = {}
    for listing in listings:
        key = _dealer_key(listing)
        if key not in groups:
            groups[key] = DealershipGroup(
                dealer_key=key,
                dealer_name=listing.get("dealer_name") or key,
                dealer_email=listing.get("dealer_email"),
                dealer_phone=listing.get("dealer_phone"),
                cars=[],
            )
        groups[key]["cars"].append(listing)
    return list(groups.values())


async def _load_order(order_id: str) -> Order | None:
    async with async_session() as session:
        result = await session.execute(
            select(Order)
            .options(selectinload(Order.customer))
            .where(Order.uuid == order_id)
        )
        return result.scalar_one_or_none()


async def start_negotiation_graph(order_id: str) -> None:
    """Fan out one negotiation graph thread per dealership for the given order."""
    from car_agent.api.app import graph  # lazy import to avoid circular dep

    order = await _load_order(order_id)
    if not order:
        logger.error("start_negotiation_graph: order %s not found", order_id)
        return

    customer = order.customer
    customer_ctx: CustomerCtx = {
        "db_id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
    }

    dealership_groups = _group_by_dealership(order.selected_listings or [])
    if not dealership_groups:
        logger.warning("Order %s has no selected listings; skipping negotiation", order_id)
        return

    tasks = []
    for group in dealership_groups:
        negotiation_id = str(uuid4())
        initial: NegotiationState = {
            "negotiation_id": negotiation_id,
            "order_id": order_id,
            "customer": customer_ctx,
            "dealership": group,
            "current_stage": 1,
            "thread": [],
            "pending_checkpoint_id": None,
            "draft_subject": None,
            "draft_body": None,
            "stage_data": {},
            "reask_count": 0,
            "thread_subject": None,
            "last_inbound_message_id": None,
            "references": [],
            "status": "in_progress",
        }
        tasks.append(_run_negotiation(graph, negotiation_id, initial))

    await asyncio.gather(*tasks, return_exceptions=True)


async def _run_negotiation(graph, negotiation_id: str, initial: NegotiationState) -> None:
    """Register the negotiation thread and start the graph."""
    # Tag every log line from this negotiation's run (incl. graph node logs) with
    # its id. Safe under asyncio.gather: each gathered task gets its own context copy.
    neg_id_var.set(negotiation_id)
    # Register before starting so the inbound webhook can find us from the moment
    # the first email is sent (the graph pauses at wait_for_approval first, which
    # means the email hasn't gone out yet, but we register early to be safe).
    existing = await get_thread_id(negotiation_id)
    if not existing:
        await register_negotiation(negotiation_id, negotiation_id)

    config = {"configurable": {"thread_id": negotiation_id}}
    try:
        await graph.ainvoke(initial, config)
    except Exception:
        logger.exception("Negotiation graph thread %s failed", negotiation_id)
