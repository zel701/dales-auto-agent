"""POST /api/invites/redeem schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RedeemInviteRequest(BaseModel):
    code: str = Field(..., max_length=64)


class RedeemInviteResponse(BaseModel):
    ok: bool
    # Canonical form of the accepted code, so the website stores a normalized
    # value in its cookie regardless of how the user typed it.
    code: str
