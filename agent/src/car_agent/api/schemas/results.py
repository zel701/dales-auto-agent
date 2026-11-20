"""GET /api/results/{uuid} schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ResultsResponse(BaseModel):
    """Cached search results returned to the website.

    `car_info` and `listings` stay as dicts for now — they originate from the
    `SearchResult` JSON column. Phase 2 will reshape these into typed
    `car_agent.domain.Listing` entries when the analyze flow does the same.
    """

    car_info: dict[str, Any]
    listings: list[dict[str, Any]]
    num_found: int
    email: str
