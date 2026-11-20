"""Negotiation — a single dealer-buyer negotiation thread for one listing."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

NegotiationStatus = Literal[
    "drafting",
    "awaiting_dealer",
    "counter_received",
    "accepted",
    "rejected",
    "stalled",
    "finalized",
]

NegotiationDirection = Literal["outbound", "inbound"]


class NegotiationRound(BaseModel):
    """One message exchange in a negotiation thread.

    Maps to a `Message` ORM row. `our_offer` / `dealer_offer` are extracted
    from the message body during evaluation; they may be unset on early rounds.
    """

    model_config = ConfigDict(from_attributes=True)

    round_number: int
    direction: NegotiationDirection
    channel: Literal["email"] = "email"
    subject: Optional[str] = None
    body: str
    timestamp: datetime
    our_offer: Optional[float] = None
    dealer_offer: Optional[float] = None


class Negotiation(BaseModel):
    """Negotiation core — status, offers, and identifiers.

    Listing and rounds are loaded separately by services that need them; the
    domain entity stays flat to map 1:1 to the `negotiations` ORM table.
    """

    model_config = ConfigDict(from_attributes=True)

    negotiation_id: str
    customer_id: Optional[int] = None
    listing_id: Optional[int] = None
    status: NegotiationStatus = "drafting"
    current_offer: Optional[float] = None
    best_dealer_price: Optional[float] = None
    outcome: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    rounds: list[NegotiationRound] = Field(default_factory=list)
