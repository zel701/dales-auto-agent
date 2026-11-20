"""Score listings task: rank a set of MarketCheck listings against user preferences."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from car_agent.services.llm._base import invoke_json

_SYSTEM = """You are a car buying analyst. Score each listing on how well it matches the customer's preferences.

For each listing, assign a score from 0.0 to 1.0 based on:
- Price: closer to target_price = higher score, above max_budget = 0
- Distance: closer = higher score
- Color match: exact match = bonus, flexible = less penalty
- Trim match: exact match = bonus
- Drivetrain match: must match if specified
- Availability: vehicle_status "available" (in stock) preferred over in_transit

Return a JSON array of objects with:
- listing_id: the MarketCheck listing ID
- score: float 0.0-1.0
- reasoning: brief explanation

Sort by score descending. Respond ONLY with the JSON array."""


class ListingScore(BaseModel):
    """LLM-assigned score for a single listing, keyed by MarketCheck id."""

    listing_id: str
    score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = ""


async def score_listings(
    *,
    preferences: dict[str, Any],
    listings: list[dict[str, Any]],
) -> list[ListingScore]:
    """Rank each listing 0..1 against the customer's preferences."""
    prefs_summary = {
        "make": preferences["make"],
        "model": preferences["model"],
        "trim": preferences.get("trim"),
        "color": preferences.get("exterior_color"),
        "drivetrain": preferences.get("drivetrain"),
        "target_price": preferences["target_price"],
        "max_budget": preferences["max_budget"],
        "flexible_on": preferences.get("flexible_on", []),
    }
    listings_summary = [
        {
            "listing_id": l["marketcheck_id"],
            "year": l["year"],
            "make": l["make"],
            "model": l["model"],
            "trim": l["trim"],
            "color": l["exterior_color"],
            "drivetrain": l["drivetrain"],
            "price": l["price"],
            "msrp": l["msrp"],
            "dealer": l["dealer_name"],
            "distance": l["distance_miles"],
            "in_transit": l.get("in_transit", False),
            "vehicle_status": l.get("vehicle_status"),
        }
        for l in listings
    ]
    raw = await invoke_json(
        task="score_listings",
        system=_SYSTEM,
        user=json.dumps({"preferences": prefs_summary, "listings": listings_summary}),
    )
    return [ListingScore.model_validate(item) for item in raw]
