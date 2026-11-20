"""Search service: build MarketCheck params, fetch + parse listings, score and rank, relax filters."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from car_agent.clients.marketcheck import (
    build_search_params,
    parse_listing,
    search_inventory,
)
from car_agent.services.color_search import base_color_buckets
from car_agent.services.llm.score_listings import score_listings as _llm_score_listings

logger = logging.getLogger(__name__)


def build_api_params(preferences: dict[str, Any]) -> dict[str, Any]:
    """Translate preferences into MarketCheck query params."""
    return build_search_params(
        make=preferences["make"],
        model=preferences["model"],
        year=2026,
        trim=preferences.get("trim"),
        base_ext_color=base_color_buckets(preferences.get("exterior_color")),
        drivetrain=preferences.get("drivetrain"),
        zip_code=preferences.get("zip_code"),
        radius=preferences.get("travel_radius_miles", 50),
        car_type="new",
        price_max=preferences.get("max_budget"),
    )


_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Upgrade-Insecure-Requests": "1",
}


async def _is_listing_available(vdp_url: str) -> bool:
    """GET-check a VDP URL with browser-like headers. A redirect means the listing
    is gone (dealer redirected to homepage/search). Fail-open on exceptions."""
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            resp = await client.get(vdp_url, headers=_BROWSER_HEADERS)
        return 200 <= resp.status_code < 300
    except Exception:
        return True


def _availability_tier(listing: dict) -> int:
    """Return sort tier: 0=available (in stock), 1=in transit, 2=coming soon."""
    if listing.get("in_transit"):
        return 1
    status = (listing.get("vehicle_status") or "").lower()
    if status == "available":
        return 0
    return 2  # coming soon / in production


async def filter_available_listings(
    listings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Filter and sort listings by availability.

    Excludes "coming soon" (in production) listings unless they're the only
    results. Sorts available (in stock) before in-transit. Removes stale
    VDP URLs for in-stock listings.
    """
    coming_soon = [l for l in listings if _availability_tier(l) == 2]
    actionable = [l for l in listings if _availability_tier(l) < 2]

    if not actionable:
        logger.info("Only coming-soon listings found; including %d as fallback", len(coming_soon))
        actionable = coming_soon
    elif coming_soon:
        logger.info("Excluded %d coming-soon listings", len(coming_soon))

    on_lot = [l for l in actionable if not l.get("in_transit")]
    in_transit = [l for l in actionable if l.get("in_transit")]

    async def _check(listing: dict) -> bool:
        url = listing.get("vdp_url")
        return await _is_listing_available(url) if url else True

    checks = await asyncio.gather(*[_check(l) for l in on_lot])
    verified_on_lot = [l for l, ok in zip(on_lot, checks) if ok]
    stale_count = len(on_lot) - len(verified_on_lot)
    if stale_count:
        logger.info("Filtered %d stale listings", stale_count)
    if in_transit:
        logger.info("Including %d in-transit listings", len(in_transit))

    return verified_on_lot + in_transit


async def fetch_listings(
    api_params: dict[str, Any],
    rows: int = 50,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Hit MarketCheck and parse the response. Returns (raw_listings, parsed_listings)."""
    result = await search_inventory(api_params, rows=rows)
    raw = result.get("listings", [])
    parsed = [parse_listing(r) for r in raw]
    return raw, parsed


async def score_and_rank(
    preferences: dict[str, Any],
    listings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Score listings via the LLM and return them sorted by score descending.

    Mutates each listing dict to add a `score` key, defaulting to 0.5 for any
    listing the LLM didn't include in its response.
    """
    if not listings:
        return []
    scores = await _llm_score_listings(preferences=preferences, listings=listings)
    score_map = {s.listing_id: s.score for s in scores}
    for l in listings:
        l["score"] = score_map.get(l["marketcheck_id"], 0.5)
    listings.sort(key=lambda x: x.get("score", 0), reverse=True)
    return listings


def relax_search(
    api_params: dict[str, Any],
    iteration: int,
    flexible_on: list[str],
) -> dict[str, Any]:
    """Return a widened copy of api_params for the given refinement iteration."""
    params = dict(api_params)
    if iteration == 1:
        params["radius"] = params.get("radius", 50) + 25
    elif iteration == 2:
        if "color" in flexible_on:
            params.pop("base_ext_color", None)
        else:
            params["radius"] = params.get("radius", 75) + 25
    elif iteration == 3:
        if "trim" in flexible_on:
            params.pop("trim", None)
        params.pop("base_ext_color", None)
    return params
