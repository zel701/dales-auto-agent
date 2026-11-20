"""Analysis service — search inventory, draft email, queue for human review."""

from __future__ import annotations

import logging
import os
from typing import Any
from uuid import uuid4

from car_agent.clients.marketcheck import build_search_params, parse_listing, search_inventory
from car_agent.db.repositories.customer_repo import get_or_create_customer
from car_agent.db.repositories.review_checkpoint_repo import create_checkpoint
from car_agent.db.repositories.search_result_repo import create_search_result
from car_agent.services.color_search import base_color_buckets, filter_by_color
from car_agent.services.email_templates import wrap_analysis_email
from car_agent.services.llm.analysis import generate_analysis_email
from car_agent.services.search_service import filter_available_listings

logger = logging.getLogger(__name__)

WEBSITE_URL = os.environ.get("WEBSITE_URL", "http://localhost:3000")


async def run_analysis(
    car_info: dict[str, str],
    email: str,
) -> dict[str, Any]:
    """Search MarketCheck, draft an analysis email, queue it for human review.

    The email is NOT sent here — a `ReviewCheckpoint` row is persisted in
    `pending` status. A reviewer approves it via /api/reviews/{id}/approve,
    which is where send_email actually runs.
    """
    # Two-tier color search: query by MarketCheck's normalized base color
    # buckets (recall-safe against dealer-entered color strings), then
    # post-filter by the exact marketing names the user picked.
    colors = car_info.get("colors") or []
    api_params = build_search_params(
        make=car_info["make"],
        model=car_info["model"],
        trim=car_info.get("trims"),
        base_ext_color=base_color_buckets(colors),
        zip_code=car_info.get("zipcode"),
        radius=int(car_info["radius"]) if car_info.get("radius") else None,
        car_type="new",
    )
    raw_response = await search_inventory(api_params, rows=50)
    all_listings = [parse_listing(r) for r in raw_response.get("listings", [])]
    color_listings, exact_color = filter_by_color(all_listings, colors)
    if colors and not exact_color and all_listings:
        logger.info(
            "No exact matches for colors %s among %d listings; keeping same-family near matches",
            colors, len(all_listings),
        )
    listings = await filter_available_listings(color_listings)
    num_found = len(listings)
    logger.info(
        "MarketCheck search complete",
        extra={"make": car_info["make"], "model": car_info["model"], "num_found": num_found},
    )

    customer = await get_or_create_customer(email)

    results_id = str(uuid4())
    await create_search_result(
        uuid=results_id,
        customer_id=customer.id,
        car_info=car_info,
        listings=listings,
        num_found=num_found,
    )

    logger.info("Generating analysis email", extra={"results_id": results_id})
    analysis_email = await generate_analysis_email(
        car_info=car_info,
        listings=listings,
        num_found=num_found,
    )

    results_url = f"{WEBSITE_URL}/results/{results_id}"
    full_html = wrap_analysis_email(analysis_email.html_body, car_info, results_url)

    checkpoint_id = str(uuid4())
    trims_label = "/".join(car_info.get("trims") or [])
    title = (
        f"Initial Strategy Email — {car_info['make']} {car_info['model']} "
        f"{trims_label}".strip()
    )
    await create_checkpoint(
        id=checkpoint_id,
        kind="initial_strategy_email",
        customer_id=customer.id,
        title=title,
        search_result_id=results_id,
        payload={
            "car_info": car_info,
            "marketcheck_raw": raw_response,
            "listings": listings,
            "num_found": num_found,
            "email": {
                "to": email,
                "subject": analysis_email.subject,
                "html_body": analysis_email.html_body,
                "full_html": full_html,
            },
        },
    )

    logger.info(
        "Analysis queued for review",
        extra={
            "checkpoint_id": checkpoint_id,
            "results_id": results_id,
            "num_found": num_found,
        },
    )
    return {
        "success": True,
        "queued_for_review": True,
        "checkpoint_id": checkpoint_id,
        "subject": analysis_email.subject,
        "num_found": num_found,
        "results_id": results_id,
        "customer_id": customer.id,
    }
