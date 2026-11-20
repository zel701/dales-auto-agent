"""Customer — a single buyer using the agent."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class Customer(BaseModel):
    """A customer of the agent. `id` and `created_at` are populated from persistence."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    created_at: Optional[datetime] = None
