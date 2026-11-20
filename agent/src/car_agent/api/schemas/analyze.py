"""POST /api/analyze schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    make: str
    model: str
    trims: list[str] = Field(..., min_length=1)
    colors: list[str] = Field(..., min_length=1)
    zipcode: str
    radius: str
    email: str
    invite_code: str = Field(..., max_length=64)


class AnalyzeResponse(BaseModel):
    success: bool
    subject: str
    num_found: int
    results_id: str
    queued_for_review: bool = False
    checkpoint_id: Optional[str] = None
    dry_run: Optional[bool] = None
    error: Optional[str] = None
