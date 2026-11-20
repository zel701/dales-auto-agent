"""Invitation code ORM model — closed-beta access gate."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from car_agent.db.models.base import Base


class InviteCode(Base):
    """A single-use invitation code.

    Stored in plaintext on purpose: these are low-value capability tokens, not
    credentials, and keeping them readable means `--list` can show at a glance
    which code went to whom and whether it was spent.

    Lifecycle: a code may be *unlocked* any number of times (each unlock just
    reveals the wizard) but *consumed* exactly once, when the holder submits an
    initial analysis request.
    """

    __tablename__ = "invite_codes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(64), index=True)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    unlocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    unlock_count: Mapped[int] = mapped_column(Integer, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    customer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("customers.id"), nullable=True, index=True
    )
    search_result_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("search_results.uuid"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
