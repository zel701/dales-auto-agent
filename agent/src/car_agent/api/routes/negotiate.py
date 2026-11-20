"""POST /api/negotiate — accept a negotiation request for selected listings."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from car_agent.api.schemas import NegotiateRequest, NegotiateResponse
from car_agent.db.repositories.customer_repo import (
    get_or_create_customer,
    set_customer_contact,
)
from car_agent.db.repositories.order_repo import create_order
from car_agent.db.repositories.review_checkpoint_repo import create_checkpoint
from car_agent.db.repositories.search_result_repo import (
    get_search_result,
    mark_search_result_completed,
)
from car_agent.services.email_templates import build_order_confirmation_email

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/negotiate", response_model=NegotiateResponse)
async def negotiate(req: NegotiateRequest) -> NegotiateResponse:
    """Accept a negotiation request for selected listings."""
    logger.info(
        "/api/negotiate received",
        extra={
            "results_id": req.results_id,
            "num_selected": len(req.selected_listing_ids),
        },
    )
    row = await get_search_result(req.results_id)
    if not row:
        raise HTTPException(status_code=404, detail="Results not found")
    if row.status == "completed":
        raise HTTPException(
            status_code=410,
            detail="This request has already been submitted.",
        )

    customer_email = row.customer.email
    # The negotiate-for-me step is the user-facing "you have a profile now"
    # moment. The DB row may have existed since /api/analyze; we resolve
    # idempotently in case email differs (it shouldn't).
    customer = await get_or_create_customer(customer_email)
    # Name and phone are asked for here, not at search time. Persist them before
    # the graph starts below — it reads them off the customer row to address the
    # dealer and to hand over contact details once a price is agreed.
    await set_customer_contact(
        customer.id, name=req.first_name, phone=req.phone
    )

    selected = [
        l for l in row.listings
        if l.get("marketcheck_id") in req.selected_listing_ids
           or l.get("vin") in req.selected_listing_ids
    ]

    order_id = str(uuid4())
    await create_order(
        uuid=order_id,
        search_result_id=req.results_id,
        customer_id=customer.id,
        car_info=row.car_info,
        selected_listings=selected,
        need_by_date=datetime.combine(req.need_by_date, time.min, tzinfo=timezone.utc),
        payment_method=req.payment_method,
        credit_score_range=req.credit_score_range,
        delivery_method=req.delivery_method,
    )
    await mark_search_result_completed(req.results_id)

    order_email = build_order_confirmation_email(
        car_info=row.car_info,
        selected_count=len(selected),
        need_by_date=req.need_by_date,
        payment_method=req.payment_method,
        delivery_method=req.delivery_method,
    )
    confirmation_checkpoint_id = str(uuid4())
    make = row.car_info.get("make", "")
    model = row.car_info.get("model", "")
    await create_checkpoint(
        id=confirmation_checkpoint_id,
        kind="order_confirmation_email",
        customer_id=customer.id,
        title=f"Order Confirmation — {make} {model}".strip(),
        search_result_id=req.results_id,
        payload={
            "order_id": order_id,
            "email": {
                "to": customer_email,
                "subject": order_email["subject"],
                "html_body": order_email["html_body"],
                "full_html": order_email["full_html"],
            },
        },
    )
    logger.info(
        "Queued order confirmation checkpoint %s for order %s",
        confirmation_checkpoint_id, order_id,
    )

    logger.info(
        "%s selected %d listings from %s (order %s, need_by=%s, pay=%s, deliver=%s)",
        customer_email, len(selected), req.results_id, order_id,
        req.need_by_date, req.payment_method, req.delivery_method,
    )
    for l in selected:
        logger.info(
            "  %s %s %s %s @ $%s (%s)",
            l.get("year"), l.get("make"), l.get("model"),
            l.get("trim"), l.get("price"), l.get("dealer_name"),
        )

    account_message = (
        f"We've created a profile for you using {customer_email}. "
        "No password needed — anytime, click Login at the top right "
        "and we'll send a 6-digit code to your inbox."
    )

    # Kick off parallel dealer negotiations in the background.
    from car_agent.services.negotiation_runner import start_negotiation_graph
    asyncio.create_task(start_negotiation_graph(order_id=order_id))

    return NegotiateResponse(
        success=True,
        message="We'll be in touch! Our team will negotiate the best deal for you.",
        selected_count=len(selected),
        customer_email=customer_email,
        account_message=account_message,
    )
