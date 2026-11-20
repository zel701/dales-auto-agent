"""UserPreferences — what the customer wants and where they are."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserPreferences(BaseModel):
    """The customer's car-buying preferences plus contact info.

    Mirrors the historical `UserPreferences` TypedDict in `state.py`.
    Combined (preferences + customer fields) for compatibility with existing
    LangGraph state usage; can be split later if needed.
    """

    model_config = ConfigDict(from_attributes=True)

    make: str
    model: str
    trim: Optional[str] = None
    exterior_color: Optional[str] = None
    interior_color: Optional[str] = None
    drivetrain: Optional[str] = None

    max_budget: float
    target_price: float

    zip_code: str
    travel_radius_miles: int

    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None

    flexible_on: list[str] = Field(default_factory=list)
