"""One-time-password repository — email-based 6-digit login codes."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from car_agent.db.database import async_session
from car_agent.db.models.auth import AuthOtp

MAX_ATTEMPTS = 5
MAX_ACTIVE_PER_EMAIL = 3


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _ttl() -> timedelta:
    return timedelta(minutes=int(os.environ.get("OTP_TTL_MINUTES", "10")))


def _gen_code() -> str:
    """Cryptographically random 6-digit numeric code, zero-padded."""
    return f"{secrets.randbelow(1_000_000):06d}"


async def create_otp(email: str) -> str:
    """Generate, store (hashed), and return a fresh 6-digit code for the email."""
    code = _gen_code()
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        session.add(AuthOtp(
            email=email,
            code_hash=_hash_code(code),
            expires_at=now + _ttl(),
        ))
        await session.commit()
    return code


async def count_active_otps(email: str) -> int:
    """Count unconsumed, unexpired OTPs for an email — used to throttle."""
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        stmt = (
            select(AuthOtp)
            .where(AuthOtp.email == email)
            .where(AuthOtp.consumed_at.is_(None))
            .where(AuthOtp.expires_at > now)
        )
        rows = (await session.execute(stmt)).scalars().all()
        return len(rows)


async def consume_otp(email: str, code: str) -> bool:
    """Validate a code and mark it consumed. Returns True on success.

    On a bad code we increment attempt_count on the latest OTP for the email
    so we can lock out brute force.
    """
    now = datetime.now(timezone.utc)
    code_hash = _hash_code(code)
    async with async_session() as session:
        stmt = (
            select(AuthOtp)
            .where(AuthOtp.email == email)
            .where(AuthOtp.consumed_at.is_(None))
            .where(AuthOtp.expires_at > now)
            .order_by(AuthOtp.created_at.desc())
        )
        candidates = (await session.execute(stmt)).scalars().all()
        if not candidates:
            return False

        # Find a hash match among unexpired unconsumed OTPs.
        match = next((row for row in candidates if row.code_hash == code_hash), None)
        if match is None:
            # Burn an attempt on the most recent OTP, lock if past threshold.
            latest = candidates[0]
            latest.attempt_count += 1
            if latest.attempt_count >= MAX_ATTEMPTS:
                latest.consumed_at = now
            await session.commit()
            return False

        if match.attempt_count >= MAX_ATTEMPTS:
            return False

        match.consumed_at = now
        await session.commit()
        return True
