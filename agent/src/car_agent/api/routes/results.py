"""GET /api/results/{uuid} — retrieve cached search results."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from car_agent.api.schemas import ResultsResponse
from car_agent.clients.marketcheck import extract_photo_url
from car_agent.db.repositories.search_result_repo import get_search_result

router = APIRouter()


def _backfill_photo_url(listing: dict) -> dict:
    """Derive photo_url from raw_json for listings stored before that field
    was extracted. Mutates and returns the listing for chaining."""
    if not listing.get("photo_url"):
        listing["photo_url"] = extract_photo_url(listing.get("raw_json"))
    return listing


@router.get("/api/results/{uuid}", response_model=ResultsResponse)
async def get_results(uuid: str) -> ResultsResponse:
    """Retrieve cached search results for the results page."""
    row = await get_search_result(uuid)
    if not row:
        raise HTTPException(status_code=404, detail="Results not found")
    if row.status == "completed":
        raise HTTPException(
            status_code=410,
            detail="This request has already been submitted. Our team will be in touch soon.",
        )
    listings = [_backfill_photo_url(dict(l)) for l in row.listings]
    return ResultsResponse(
        car_info=row.car_info,
        listings=listings,
        num_found=row.num_found,
        email=row.customer.email,
    )
