"""Negotiation thread routing for inbound webhooks."""

from __future__ import annotations

import re

from car_agent.db.repositories.thread_repo import get_thread_id, register_negotiation


def extract_negotiation_id(address: str) -> str | None:
    """Extract negotiation_id from reply-to address like deals+{id}@domain."""
    match = re.search(r"deals\+([a-f0-9\-]+)@", address)
    return match.group(1) if match else None


__all__ = [
    "extract_negotiation_id",
    "get_thread_id",
    "register_negotiation",
]
