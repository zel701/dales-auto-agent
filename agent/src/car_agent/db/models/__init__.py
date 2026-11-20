"""ORM models — import everything here so SQLAlchemy discovers all tables."""

from car_agent.db.models.auth import AuthOtp, CustomerSession
from car_agent.db.models.base import Base
from car_agent.db.models.customer import Customer
from car_agent.db.models.inbound_event import ProcessedResendEvent
from car_agent.db.models.invite import InviteCode
from car_agent.db.models.negotiation import Message, Negotiation, NegotiationThread
from car_agent.db.models.order import Order
from car_agent.db.models.review_checkpoint import ReviewCheckpoint
from car_agent.db.models.search import Listing, Search
from car_agent.db.models.search_result import SearchResult

__all__ = [
    "AuthOtp",
    "Base",
    "Customer",
    "CustomerSession",
    "InviteCode",
    "Listing",
    "Message",
    "Negotiation",
    "NegotiationThread",
    "Order",
    "ProcessedResendEvent",
    "ReviewCheckpoint",
    "Search",
    "SearchResult",
]
