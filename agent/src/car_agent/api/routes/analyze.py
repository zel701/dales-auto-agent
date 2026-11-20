"""POST /api/analyze — search inventory, generate analysis email, send it."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from car_agent.api.schemas import AnalyzeRequest, AnalyzeResponse
from car_agent.services.analysis import run_analysis
from car_agent.services.invite_service import (
    InviteError,
    assert_submittable,
    attribute,
    consume,
    release,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    # Validate and spend the invite before any expensive work. Claiming it up
    # front means a bad code costs nothing, and a second submit during the
    # 10-30s analysis is refused instead of quietly getting a free analysis.
    try:
        code = await assert_submittable(req.invite_code)
    except InviteError as exc:
        raise HTTPException(status_code=403, detail=exc.message)

    if not await consume(code):
        # Lost the race to a concurrent submit that claimed it microseconds ago.
        raise HTTPException(
            status_code=403, detail="This invitation code has already been used."
        )

    car_info = {
        "make": req.make,
        "model": req.model,
        "trims": req.trims,
        "colors": req.colors,
        "zipcode": req.zipcode,
        "radius": req.radius,
    }

    try:
        result = await run_analysis(car_info=car_info, email=req.email)
    except Exception:
        # Don't burn someone's invitation on our own outage.
        await release(code)
        raise

    await attribute(code, result["customer_id"], result["results_id"])
    return AnalyzeResponse.model_validate(result)
