"""Search and Listing ORM models (search aggregate)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from car_agent.db.models.base import Base


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"))
    params_json: Mapped[dict] = mapped_column(JSON)
    num_found: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    customer: Mapped[object] = relationship("Customer", back_populates="searches")
    listings: Mapped[list] = relationship("Listing", back_populates="search")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(ForeignKey("searches.id"))
    marketcheck_id: Mapped[str] = mapped_column(String(100))
    vin: Mapped[str] = mapped_column(String(17))
    year: Mapped[int] = mapped_column(Integer)
    make: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(50))
    trim: Mapped[str] = mapped_column(String(100))
    exterior_color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    interior_color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    drivetrain: Mapped[str | None] = mapped_column(String(20), nullable=True)
    price: Mapped[float] = mapped_column(Float)
    msrp: Mapped[float | None] = mapped_column(Float, nullable=True)
    days_on_lot: Mapped[int] = mapped_column(Integer, default=0)
    dealer_name: Mapped[str] = mapped_column(String(200))
    dealer_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dealer_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dealer_city: Mapped[str] = mapped_column(String(100))
    dealer_state: Mapped[str] = mapped_column(String(10))
    dealer_zip: Mapped[str] = mapped_column(String(10))
    distance_miles: Mapped[float] = mapped_column(Float, default=0.0)
    vdp_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON)

    search: Mapped[object] = relationship("Search", back_populates="listings")
    negotiations: Mapped[list] = relationship("Negotiation", back_populates="listing")
