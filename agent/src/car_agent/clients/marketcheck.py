"""MarketCheck API client for car inventory search."""

from __future__ import annotations

import os
from typing import Any

import httpx

BASE_URL = "https://api.marketcheck.com/v2/search/car/active"


async def search_inventory(
    params: dict[str, Any],
    rows: int = 25,
    start: int = 0,
) -> dict[str, Any]:
    """Search MarketCheck for active car inventory.

    Args:
        params: Search filters (make, model, trim, year, zip, radius,
                drivetrain, exterior_color, car_type, price_range, etc.)
        rows: Number of results per page.
        start: Pagination offset.

    Returns:
        Raw API response dict with 'num_found' and 'listings' keys.
    """
    api_key = os.environ.get("MARKETCHECK_API_KEY")
    if not api_key:
        raise ValueError("MARKETCHECK_API_KEY not set")

    query = {
        "api_key": api_key,
        "rows": rows,
        "start": start,
        **params,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(BASE_URL, params=query)
        resp.raise_for_status()
        return resp.json()


def expand_trim_variants(trims: list[str]) -> list[str]:
    """Expand configurator grade names into their likely MarketCheck trim
    spellings. MarketCheck's trim strings don't always match Toyota's grade
    names: hyphenation varies by model (Tacoma inventory is "TRD Off Road"
    while 4Runner is "TRD Off-Road"), and i-FORCE MAX grades are folded into
    the base trim name. The comma list is OR, so extra variants only add
    recall; the exact powertrain/config still distinguishes listings.
    """
    variants: list[str] = []
    for t in trims:
        base = t.removesuffix(" i-FORCE MAX")
        for v in (t, base, base.replace("-", " ")):
            if v and v not in variants:
                variants.append(v)
    return variants


def build_search_params(
    make: str,
    model: str,
    year: int | None = None,
    trim: list[str] | None = None,
    base_ext_color: list[str] | None = None,
    drivetrain: str | None = None,
    zip_code: str | None = None,
    radius: int | None = None,
    car_type: str = "new",
    price_max: float | None = None,
) -> dict[str, Any]:
    """Build MarketCheck query params from user preferences.

    `trim` and `base_ext_color` accept multiple values; MarketCheck treats
    a comma-separated list as OR (any-of). Color filtering uses MarketCheck's
    normalized base buckets (Red/White/Gray, …) rather than exact marketing
    names — see services.color_search for the exact-name post-filter tier.
    """
    params: dict[str, Any] = {
        "make": make,
        "model": model,
        "car_type": car_type,
    }
    if year:
        params["year"] = year
    if trim:
        params["trim"] = ",".join(expand_trim_variants(trim))
    if base_ext_color:
        params["base_ext_color"] = ",".join(base_ext_color)
    if drivetrain:
        params["drivetrain"] = drivetrain
    if zip_code:
        params["zip"] = zip_code
    if radius:
        params["radius"] = radius
    if price_max:
        params["price_range"] = f"0-{int(price_max)}"
    return params



def extract_photo_url(raw: dict | None) -> str | None:
    """Pull the first photo URL out of a MarketCheck `media` blob."""
    if not raw:
        return None
    media = raw.get("media") or {}
    photo_links = media.get("photo_links") or media.get("photo_links_cached") or []
    if not photo_links:
        return None
    return photo_links[0]


def parse_listing(raw: dict) -> dict[str, Any]:
    """Parse a raw MarketCheck listing into a flat dict for DB storage."""
    build = raw.get("build", {})
    dealer = raw.get("dealer", {})
    photo_url = extract_photo_url(raw)
    return {
        "marketcheck_id": raw.get("id", ""),
        "vin": raw.get("vin", ""),
        "year": build.get("year", 0),
        "make": build.get("make", ""),
        "model": build.get("model", ""),
        "trim": build.get("trim", ""),
        "exterior_color": raw.get("exterior_color"),
        "interior_color": raw.get("interior_color"),
        "drivetrain": build.get("drivetrain"),
        "price": raw.get("price", 0),
        "msrp": raw.get("msrp"),
        "days_on_lot": raw.get("dom_active", 0),
        "dealer_name": dealer.get("name", ""),
        "dealer_email": dealer.get("email"),
        "dealer_phone": dealer.get("phone"),
        "dealer_city": dealer.get("city", ""),
        "dealer_state": dealer.get("state", ""),
        "dealer_zip": dealer.get("zip", ""),
        "distance_miles": raw.get("dist", 0.0),
        "vdp_url": raw.get("vdp_url"),
        "photo_url": photo_url,
        "in_transit": bool(raw.get("in_transit", False)),
        "vehicle_status": raw.get("vehicle_status"),
        "raw_json": raw,
    }
