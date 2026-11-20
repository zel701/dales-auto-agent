"""Listing — a single car for sale at a dealership."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Listing(BaseModel):
    """Canonical car listing shape.

    Fields are flat (dealer_* prefixed) to match the SQLAlchemy ORM, the
    LangGraph state TypedDicts, and the website's TypeScript `Listing` type.
    Keep this in sync with `website/src/types/index.ts` Listing.
    """

    model_config = ConfigDict(from_attributes=True)

    marketcheck_id: str
    vin: str
    year: int
    make: str
    model: str
    trim: str

    exterior_color: Optional[str] = None
    interior_color: Optional[str] = None
    drivetrain: Optional[str] = None

    price: float
    msrp: Optional[float] = None
    days_on_lot: int = 0
    distance_miles: float = 0.0

    vdp_url: Optional[str] = None
    photo_url: Optional[str] = None
    in_transit: bool = False
    vehicle_status: Optional[str] = None

    dealer_name: str
    dealer_email: Optional[str] = None
    dealer_phone: Optional[str] = None
    dealer_city: str
    dealer_state: str
    dealer_zip: str


class ScoredListing(Listing):
    """A listing with an LLM-assigned 0..1 match score."""

    score: float = Field(..., ge=0.0, le=1.0)
