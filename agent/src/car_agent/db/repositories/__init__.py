"""Database repositories — one module per aggregate."""

from car_agent.db.repositories.customer_repo import create_customer, get_customer
from car_agent.db.repositories.listing_repo import (
    bulk_create_listings,
    get_competing_listings,
    get_listing_by_marketcheck_id,
    get_listings_by_search,
)
from car_agent.db.repositories.message_repo import (
    create_message,
    get_messages_for_negotiation,
)
from car_agent.db.repositories.negotiation_repo import (
    create_negotiation,
    get_negotiation_by_id,
    update_negotiation_status,
)
from car_agent.db.repositories.order_repo import create_order
from car_agent.db.repositories.search_repo import create_search
from car_agent.db.repositories.search_result_repo import (
    create_search_result,
    get_search_result,
)
from car_agent.db.repositories.thread_repo import get_thread_id, register_negotiation

__all__ = [
    "bulk_create_listings",
    "create_customer",
    "create_message",
    "create_negotiation",
    "create_order",
    "create_search",
    "create_search_result",
    "get_competing_listings",
    "get_customer",
    "get_listing_by_marketcheck_id",
    "get_listings_by_search",
    "get_messages_for_negotiation",
    "get_negotiation_by_id",
    "get_search_result",
    "get_thread_id",
    "register_negotiation",
    "update_negotiation_status",
]
