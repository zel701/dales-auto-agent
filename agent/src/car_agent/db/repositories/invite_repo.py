"""Invitation code repository — closed-beta access codes."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from car_agent.db.database import async_session
from car_agent.db.models.customer import Customer as CustomerORM
from car_agent.db.models.invite import InviteCode

# Crockford-ish alphabet: no 0/1/I/L/O/U, so a code survives being read aloud
# or retyped from a text message.
ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"
PREFIX = "DALE"
BODY_LENGTH = 4

_CANONICAL_RE = re.compile(rf"^{PREFIX}-[{ALPHABET}]{{{BODY_LENGTH}}}$")


def generate_code() -> str:
    """A fresh random code in canonical `DALE-XXXX` form."""
    body = "".join(secrets.choice(ALPHABET) for _ in range(BODY_LENGTH))
    return f"{PREFIX}-{body}"


def normalize_code(raw: str) -> str | None:
    """Coerce user input to canonical form, or None if it can't be one.

    Accepts `dale7k3m`, `DALE 7K3M`, `dale-7k3m`, and the bare body `7k3m`
    (the prefix is constant, so people drop it). Returning None lets callers
    reject junk without touching the database.
    """
    if not raw:
        return None
    stripped = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
    if stripped.startswith(PREFIX):
        stripped = stripped[len(PREFIX):]
    candidate = f"{PREFIX}-{stripped}"
    return candidate if _CANONICAL_RE.match(candidate) else None


async def create_invite_codes(
    count: int, label_prefix: str, note: str | None = None
) -> list[InviteCode]:
    """Generate `count` codes with sequential labels (`batch1-001`, ...).

    In a 30^4 space, 100 draws collide often (birthday paradox: ~0.6% per pair,
    ~0.6 expected collisions per batch), so codes are drawn against the set of
    existing ones and against each other before any insert.
    """
    async with async_session() as session:
        taken = set((await session.execute(select(InviteCode.code))).scalars().all())
        if len(taken) + count > len(ALPHABET) ** BODY_LENGTH // 2:
            raise RuntimeError(
                "Refusing to generate: the code space is over half full, which "
                "makes guessing far too easy. Widen BODY_LENGTH first."
            )

        rows: list[InviteCode] = []
        for i in range(1, count + 1):
            code = generate_code()
            while code in taken:
                code = generate_code()
            taken.add(code)
            rows.append(
                InviteCode(code=code, label=f"{label_prefix}-{i:03d}", note=note)
            )

        session.add_all(rows)
        try:
            await session.commit()
        except IntegrityError as exc:  # label/code raced with another run
            await session.rollback()
            raise RuntimeError(f"Code generation collided, nothing written: {exc}")
    return rows


async def get_invite_by_code(code: str) -> InviteCode | None:
    async with async_session() as session:
        stmt = select(InviteCode).where(InviteCode.code == code)
        return (await session.execute(stmt)).scalar_one_or_none()


async def mark_unlocked(code: str) -> InviteCode | None:
    """Record a successful unlock. Returns None if the code is unknown or revoked.

    A consumed code still unlocks — the holder already spent it, so re-locking
    them out of the site they just used would be hostile.
    """
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        stmt = select(InviteCode).where(InviteCode.code == code)
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None or row.revoked_at is not None:
            return None
        if row.unlocked_at is None:
            row.unlocked_at = now
        row.unlock_count += 1
        await session.commit()
        return row


async def consume_invite_code(
    code: str,
    customer_id: str | None = None,
    search_result_id: str | None = None,
) -> bool:
    """Spend the code. False means it was already spent or revoked.

    A single conditional UPDATE, so two concurrent submits with the same code
    cannot both win — the loser gets rowcount 0.

    The caller may spend the code before it knows who is spending it (the
    customer and search result only exist once the analysis has run) and fill
    those in afterwards with `attribute_invite_code`.
    """
    now = datetime.now(timezone.utc)
    values: dict = {"consumed_at": now}
    if customer_id is not None:
        values["customer_id"] = customer_id
    if search_result_id is not None:
        values["search_result_id"] = search_result_id

    async with async_session() as session:
        stmt = (
            update(InviteCode)
            .where(InviteCode.code == code)
            .where(InviteCode.consumed_at.is_(None))
            .where(InviteCode.revoked_at.is_(None))
            .values(**values)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount == 1


async def attribute_invite_code(
    code: str, customer_id: str, search_result_id: str
) -> None:
    """Record who spent an already-consumed code and what it bought."""
    async with async_session() as session:
        stmt = (
            update(InviteCode)
            .where(InviteCode.code == code)
            .values(customer_id=customer_id, search_result_id=search_result_id)
        )
        await session.execute(stmt)
        await session.commit()


async def release_invite_code(code: str) -> None:
    """Un-spend a code. Used when the work it paid for failed, so an outage
    doesn't silently burn someone's invitation."""
    async with async_session() as session:
        stmt = (
            update(InviteCode)
            .where(InviteCode.code == code)
            .values(consumed_at=None, customer_id=None, search_result_id=None)
        )
        await session.execute(stmt)
        await session.commit()


async def revoke_invite_code(code: str) -> bool:
    """Kill a code. Idempotent: returns False if unknown or already revoked."""
    async with async_session() as session:
        stmt = (
            update(InviteCode)
            .where(InviteCode.code == code)
            .where(InviteCode.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount == 1


async def set_note(label: str, note: str) -> bool:
    """Attach a note to a code by label, once you know who you sent it to."""
    async with async_session() as session:
        stmt = update(InviteCode).where(InviteCode.label == label).values(note=note)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount == 1


async def list_invite_codes(
    status: str | None = None,
) -> list[tuple[InviteCode, str | None]]:
    """All codes with the email of whoever spent them, newest label last.

    `status` filters to one of active / consumed / revoked.
    """
    async with async_session() as session:
        stmt = (
            select(InviteCode, CustomerORM.email)
            .outerjoin(CustomerORM, InviteCode.customer_id == CustomerORM.id)
            .order_by(InviteCode.label)
        )
        if status == "active":
            stmt = stmt.where(
                InviteCode.consumed_at.is_(None), InviteCode.revoked_at.is_(None)
            )
        elif status == "consumed":
            stmt = stmt.where(InviteCode.consumed_at.is_not(None))
        elif status == "revoked":
            stmt = stmt.where(InviteCode.revoked_at.is_not(None))
        return [(row, email) for row, email in (await session.execute(stmt)).all()]
