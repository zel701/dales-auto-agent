"""Customer session repository — opaque login tokens."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from car_agent.db.database import async_session
from car_agent.db.models.auth import CustomerSession
from car_agent.db.models.customer import Customer as CustomerORM


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _ttl() -> timedelta:
    return timedelta(days=int(os.environ.get("SESSION_TTL_DAYS", "30")))


async def create_session(customer_id: str) -> str:
    """Mint a fresh session for the customer; returns the raw token (only time
    the caller sees it — only the hash is stored)."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        session.add(CustomerSession(
            customer_id=customer_id,
            token_hash=_hash_token(token),
            expires_at=now + _ttl(),
        ))
        await session.commit()
    return token


async def get_customer_for_token(token: str) -> CustomerORM | None:
    """Resolve a raw session token to a Customer ORM row, or None if the
    token is unknown / expired / revoked."""
    token_hash = _hash_token(token)
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        stmt = (
            select(CustomerSession, CustomerORM)
            .join(CustomerORM, CustomerSession.customer_id == CustomerORM.id)
            .where(CustomerSession.token_hash == token_hash)
        )
        result = (await session.execute(stmt)).first()
        if result is None:
            return None
        sess, customer = result
        if sess.revoked_at is not None:
            return None
        # Postgres (timestamptz) returns aware datetimes; SQLite returns naive
        # UTC — normalize before comparing.
        expires_at = sess.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            return None
        return customer


async def revoke_session(token: str) -> None:
    """Mark a session as revoked. Idempotent: silent if token unknown."""
    token_hash = _hash_token(token)
    async with async_session() as session:
        stmt = select(CustomerSession).where(CustomerSession.token_hash == token_hash)
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None or row.revoked_at is not None:
            return
        row.revoked_at = datetime.now(timezone.utc)
        await session.commit()
