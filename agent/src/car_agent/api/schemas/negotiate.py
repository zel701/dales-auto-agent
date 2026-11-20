"""POST /api/negotiate schemas."""

from __future__ import annotations

import re
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator

CreditScoreRange = Literal[
    "780_plus", "720_779", "660_719", "600_659", "under_600"
]


class NegotiateRequest(BaseModel):
    """Request body for POST /api/negotiate."""

    results_id: str
    selected_listing_ids: list[str]
    first_name: str
    phone: str
    need_by_date: date
    payment_method: Literal["finance", "cash"]
    credit_score_range: Optional[CreditScoreRange] = None
    delivery_method: Literal["pickup", "ship"]

    @field_validator("first_name")
    @classmethod
    def _strip_first_name(cls, v: str) -> str:
        name = v.strip()
        if not name:
            raise ValueError("first_name is required")
        return name

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, v: str) -> str:
        """Accept any punctuation, store bare 10-digit US numbers."""
        digits = re.sub(r"\D", "", v)
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) != 10:
            raise ValueError("phone must be a 10-digit US phone number")
        return digits

    @model_validator(mode="after")
    def _credit_range_required_for_finance(self) -> "NegotiateRequest":
        # The website only asks financed buyers for a tier, but this API is
        # reachable on its own, so the rule is enforced here too.
        if self.payment_method == "finance" and self.credit_score_range is None:
            raise ValueError("credit_score_range is required when payment_method is finance")
        return self


class NegotiateResponse(BaseModel):
    """Response for POST /api/negotiate."""

    success: bool
    message: str
    selected_count: int
    customer_email: str
    account_message: str
