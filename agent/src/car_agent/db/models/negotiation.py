"""Negotiation, Message, and NegotiationThread ORM models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from car_agent.db.models.base import Base


class Negotiation(Base):
    __tablename__ = "negotiations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    negotiation_id: Mapped[str] = mapped_column(String(36), unique=True)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"))
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    status: Mapped[str] = mapped_column(String(30), default="drafting")
    current_offer: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_dealer_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    customer: Mapped[object] = relationship("Customer", back_populates="negotiations")
    listing: Mapped[object] = relationship("Listing", back_populates="negotiations")
    messages: Mapped[list] = relationship("Message", back_populates="negotiation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    negotiation_id: Mapped[int] = mapped_column(ForeignKey("negotiations.id"))
    direction: Mapped[str] = mapped_column(String(10))
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    sendgrid_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    negotiation: Mapped[object] = relationship("Negotiation", back_populates="messages")


class NegotiationThread(Base):
    """Maps negotiation_id to LangGraph thread_id for webhook routing."""

    __tablename__ = "negotiation_threads"

    negotiation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
