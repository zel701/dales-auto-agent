"""Unit tests for the score_listings LLM task."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from car_agent.services.llm.score_listings import ListingScore, score_listings

PREFS = {
    "make": "Toyota",
    "model": "Camry",
    "trim": "XSE",
    "exterior_color": "white",
    "drivetrain": "FWD",
    "target_price": 28_000,
    "max_budget": 31_000,
    "flexible_on": [],
}

LISTINGS = [
    {
        "marketcheck_id": "L1",
        "year": 2024,
        "make": "Toyota",
        "model": "Camry",
        "trim": "XSE",
        "exterior_color": "white",
        "drivetrain": "FWD",
        "price": 28_500,
        "msrp": 30_000,
        "dealer_name": "ABC Toyota",
        "distance_miles": 10,
        "days_on_lot": 45,
    },
    {
        "marketcheck_id": "L2",
        "year": 2024,
        "make": "Toyota",
        "model": "Camry",
        "trim": "SE",
        "exterior_color": "black",
        "drivetrain": "FWD",
        "price": 26_000,
        "msrp": 27_500,
        "dealer_name": "XYZ Auto",
        "distance_miles": 35,
        "days_on_lot": 10,
    },
]

LLM_RESPONSE = [
    {"listing_id": "L1", "score": 0.9, "reasoning": "Exact match on trim and color"},
    {"listing_id": "L2", "score": 0.6, "reasoning": "Wrong trim and color"},
]


@pytest.mark.asyncio
async def test_score_listings_returns_typed_scores():
    with patch(
        "car_agent.services.llm.score_listings.invoke_json",
        new=AsyncMock(return_value=LLM_RESPONSE),
    ):
        scores = await score_listings(preferences=PREFS, listings=LISTINGS)

    assert len(scores) == 2
    assert all(isinstance(s, ListingScore) for s in scores)
    assert scores[0].listing_id == "L1"
    assert scores[0].score == pytest.approx(0.9)
    assert scores[1].score == pytest.approx(0.6)


@pytest.mark.asyncio
async def test_score_listings_passes_correct_listing_ids():
    captured: list = []

    async def capture_invoke(**kwargs):
        captured.append(kwargs["user"])
        return LLM_RESPONSE

    with patch(
        "car_agent.services.llm.score_listings.invoke_json",
        new=capture_invoke,
    ):
        await score_listings(preferences=PREFS, listings=LISTINGS)

    import json

    user_payload = json.loads(captured[0])
    ids = [l["listing_id"] for l in user_payload["listings"]]
    assert ids == ["L1", "L2"]
