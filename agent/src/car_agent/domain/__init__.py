"""Domain entities — the canonical shapes used across persistence, state, and API.

Entities here are framework-agnostic Pydantic models. They map cleanly to the
SQLAlchemy ORM rows in `db/models_db.py` (via `from_attributes=True`) and to
the request/response shapes in `api/routes/schemas.py`.

Add a new entity when you find data being passed around in three different
shapes (TypedDict, ORM row, dict) — give it one home.
"""

from car_agent.domain.customer import Customer
from car_agent.domain.listing import Listing, ScoredListing
from car_agent.domain.negotiation import (
    Negotiation,
    NegotiationDirection,
    NegotiationRound,
    NegotiationStatus,
)
from car_agent.domain.user_preferences import UserPreferences

__all__ = [
    "Customer",
    "Listing",
    "ScoredListing",
    "Negotiation",
    "NegotiationRound",
    "NegotiationStatus",
    "NegotiationDirection",
    "UserPreferences",
]
