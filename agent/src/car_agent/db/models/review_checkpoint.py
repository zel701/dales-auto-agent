"""ReviewCheckpoint ORM model — human-in-the-loop approval packets."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from car_agent.db.models.base import Base


class ReviewCheckpoint(Base):
    """A packet of work awaiting human approval before an agent action runs.

    Today the only `kind` is `initial_strategy_email` (drafted analysis email
    held back from sending until a reviewer approves). New kinds can extend
    the table without a migration: the `payload` JSON column carries the
    kind-specific shape.
    """

    __tablename__ = "review_checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    search_result_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("search_results.uuid"), nullable=True, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    actor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    acted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped[object] = relationship("Customer", lazy="joined")

    __table_args__ = (
        Index("ix_review_checkpoints_status_created", "status", "created_at"),
    )
