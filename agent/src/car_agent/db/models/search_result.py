"""SearchResult ORM model — cached search results for email CTA links."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from car_agent.db.models.base import Base


class SearchResult(Base):
    __tablename__ = "search_results"

    uuid: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id"), index=True
    )
    car_info: Mapped[dict] = mapped_column(JSON)
    listings: Mapped[list] = mapped_column(JSON)
    num_found: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    customer: Mapped[object] = relationship("Customer", lazy="joined")
