"""Schemas for /api/reviews endpoints (HITL approval packets)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ReviewSummary(BaseModel):
    id: str
    kind: str
    status: str
    title: str
    customer_email: str
    created_at: datetime
    updated_at: datetime


class ReviewListResponse(BaseModel):
    items: list[ReviewSummary]


class ReviewDetail(BaseModel):
    id: str
    kind: str
    status: str
    title: str
    customer_email: str
    search_result_id: Optional[str] = None
    payload: dict[str, Any]
    result: Optional[dict[str, Any]] = None
    actor: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    acted_at: Optional[datetime] = None


class CancelRequest(BaseModel):
    reason: Optional[str] = None


class SendOutcome(BaseModel):
    success: bool
    dry_run: bool
    error: Optional[str] = None
    message_id: Optional[str] = None


class ApproveResponse(BaseModel):
    success: bool
    send_result: SendOutcome


class CancelResponse(BaseModel):
    success: bool
