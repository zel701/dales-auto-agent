"""ProcessedResendEvent — deduplication table for inbound Resend webhook events."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from car_agent.db.models.base import Base


class ProcessedResendEvent(Base):
    """Tracks processed Resend inbound event IDs to prevent double-processing on retries."""

    __tablename__ = "processed_resend_events"

    event_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
