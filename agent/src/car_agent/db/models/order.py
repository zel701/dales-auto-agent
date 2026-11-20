"""Order ORM model — customer negotiation requests with metadata."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from car_agent.db.models.base import Base


class Order(Base):
    __tablename__ = "orders"

    uuid: Mapped[str] = mapped_column(String(36), primary_key=True)
    search_result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("search_results.uuid")
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id"), index=True
    )
    car_info: Mapped[dict] = mapped_column(JSON)
    selected_listings: Mapped[list] = mapped_column(JSON)
    need_by_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payment_method: Mapped[str] = mapped_column(String(20))
    # Only collected for financed orders; nullable for cash and for rows
    # predating the field.
    credit_score_range: Mapped[str | None] = mapped_column(String(20), nullable=True)
    delivery_method: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="submitted")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    customer: Mapped[object] = relationship("Customer")
