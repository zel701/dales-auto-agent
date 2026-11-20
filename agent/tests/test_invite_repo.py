"""Invitation code repository + service tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from car_agent.db.repositories.customer_repo import get_or_create_customer
from car_agent.db.repositories.invite_repo import (
    ALPHABET,
    BODY_LENGTH,
    attribute_invite_code,
    consume_invite_code,
    create_invite_codes,
    generate_code,
    get_invite_by_code,
    list_invite_codes,
    mark_unlocked,
    normalize_code,
    release_invite_code,
    revoke_invite_code,
    set_note,
)
from car_agent.db.repositories.search_result_repo import create_search_result
from car_agent.services.invite_service import (
    ConsumedInviteError,
    InvalidInviteError,
    assert_submittable,
    redeem_for_unlock,
)


@pytest.fixture
async def customer():
    return await get_or_create_customer("invite-test@example.com")


def _utc(dt: datetime) -> datetime:
    """Postgres (timestamptz) returns aware datetimes; SQLite returns naive UTC.
    Same normalization as session_repo.get_customer_for_token."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


async def _make_code(label: str) -> str:
    rows = await create_invite_codes(1, label)
    return rows[0].code


async def _make_search_result(customer_id: str, uuid: str) -> str:
    await create_search_result(
        uuid=uuid,
        customer_id=customer_id,
        car_info={"make": "Toyota", "model": "RAV4"},
        listings=[],
        num_found=0,
    )
    return uuid


def test_generate_code_shape():
    for _ in range(50):
        code = generate_code()
        prefix, body = code.split("-")
        assert prefix == "DALE"
        assert len(body) == BODY_LENGTH
        assert all(c in ALPHABET for c in body)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("DALE-7K3M", "DALE-7K3M"),
        ("dale-7k3m", "DALE-7K3M"),
        ("dale7k3m", "DALE-7K3M"),
        ("DALE 7K3M", "DALE-7K3M"),
        ("  7k3m  ", "DALE-7K3M"),  # bare body — people drop the constant prefix
        ("7K3M", "DALE-7K3M"),
    ],
)
def test_normalize_code_accepts(raw, expected):
    assert normalize_code(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "DALE",
        "DALE-7K3",  # too short
        "DALE-7K3MM",  # too long
        "DALE-70IM",  # 0 and I are not in the alphabet
        "not a code at all",
        "DALE-7K3M-92XQ",  # the old two-block format
    ],
)
def test_normalize_code_rejects(raw):
    assert normalize_code(raw) is None


async def test_create_invite_codes_are_unique_and_labelled():
    rows = await create_invite_codes(100, "uniqbatch")

    assert len(rows) == 100
    assert len({r.code for r in rows}) == 100, "collision slipped through"
    assert rows[0].label == "uniqbatch-001"
    assert rows[-1].label == "uniqbatch-100"
    assert all(normalize_code(r.code) == r.code for r in rows)

    # And they don't collide with codes already in the table.
    more = await create_invite_codes(50, "uniqbatch2")
    assert len({r.code for r in rows} & {r.code for r in more}) == 0


async def test_create_invite_codes_applies_batch_note():
    rows = await create_invite_codes(2, "notedbatch", note="Reddit drop")
    assert all(r.note == "Reddit drop" for r in rows)


async def test_unlock_stamps_and_counts():
    code = await _make_code("unlockbatch")

    first = await mark_unlocked(code)
    assert first is not None
    assert first.unlocked_at is not None
    assert first.unlock_count == 1

    second = await mark_unlocked(code)
    assert second.unlock_count == 2
    # unlocked_at records the *first* unlock, so it must not move.
    assert _utc(second.unlocked_at) == _utc(first.unlocked_at)


async def test_consume_marks_and_attributes(customer):
    code = await _make_code("consumebatch")
    results_id = await _make_search_result(customer.id, "res-consume-1")

    assert await consume_invite_code(code, customer.id, results_id) is True

    row = await get_invite_by_code(code)
    assert row.consumed_at is not None
    assert row.customer_id == customer.id
    assert row.search_result_id == results_id


async def test_consume_is_single_use(customer):
    code = await _make_code("singleusebatch")
    first = await _make_search_result(customer.id, "res-single-1")
    second = await _make_search_result(customer.id, "res-single-2")

    assert await consume_invite_code(code, customer.id, first) is True
    assert await consume_invite_code(code, customer.id, second) is False

    # The losing submit must not overwrite the attribution of the winner.
    row = await get_invite_by_code(code)
    assert row.search_result_id == first


async def test_consume_up_front_then_attribute(customer):
    """The route spends the code before the analysis has produced a customer
    or a search result, then fills them in afterwards."""
    code = await _make_code("attributebatch")

    assert await consume_invite_code(code) is True
    row = await get_invite_by_code(code)
    assert row.consumed_at is not None
    assert row.customer_id is None
    assert row.search_result_id is None

    # Spent means spent, even before it has been attributed — this is what
    # blocks a second submit during the 10-30s analysis window.
    assert await consume_invite_code(code) is False

    results_id = await _make_search_result(customer.id, "res-attribute-1")
    await attribute_invite_code(code, customer.id, results_id)

    row = await get_invite_by_code(code)
    assert row.customer_id == customer.id
    assert row.search_result_id == results_id
    assert row.consumed_at is not None


async def test_release_returns_a_code_to_the_pool(customer):
    """A failed analysis must not burn the invitation."""
    code = await _make_code("releasebatch")
    assert await consume_invite_code(code) is True

    await release_invite_code(code)

    row = await get_invite_by_code(code)
    assert row.consumed_at is None
    assert row.customer_id is None
    assert row.search_result_id is None
    # Usable again, both for submitting and for a fresh consume.
    assert await assert_submittable(code) == code
    assert await consume_invite_code(code) is True


async def test_unlock_still_works_after_consume(customer):
    """The holder just spent their code on the site; don't lock them back out."""
    code = await _make_code("afterconsumebatch")
    results_id = await _make_search_result(customer.id, "res-after-1")
    await consume_invite_code(code, customer.id, results_id)

    assert await mark_unlocked(code) is not None
    assert await redeem_for_unlock(code) == code


async def test_revoked_code_rejected_for_unlock_and_consume(customer):
    code = await _make_code("revokedbatch")
    assert await revoke_invite_code(code) is True

    assert await mark_unlocked(code) is None
    assert await redeem_for_unlock(code) is None

    results_id = await _make_search_result(customer.id, "res-revoked-1")
    assert await consume_invite_code(code, customer.id, results_id) is False

    # Revoking twice is a no-op, not an error.
    assert await revoke_invite_code(code) is False


async def test_redeem_for_unlock_normalizes_input():
    code = await _make_code("normbatch")
    body = code.split("-")[1]

    assert await redeem_for_unlock(body.lower()) == code
    assert await redeem_for_unlock(f"  {code.lower()}  ") == code
    assert await redeem_for_unlock("nonsense") is None


async def test_assert_submittable_distinguishes_failures(customer):
    code = await _make_code("submitbatch")

    assert await assert_submittable(code.lower()) == code

    with pytest.raises(InvalidInviteError):
        await assert_submittable("DALE-ZZZZ")
    with pytest.raises(InvalidInviteError):
        await assert_submittable("garbage")

    results_id = await _make_search_result(customer.id, "res-submit-1")
    await consume_invite_code(code, customer.id, results_id)
    with pytest.raises(ConsumedInviteError):
        await assert_submittable(code)


async def test_set_note_and_list_filters(customer):
    rows = await create_invite_codes(3, "listbatch")
    results_id = await _make_search_result(customer.id, "res-list-1")
    await consume_invite_code(rows[0].code, customer.id, results_id)
    await revoke_invite_code(rows[1].code)
    assert await set_note("listbatch-003", "Sarah") is True

    by_label = {row.label: (row, email) for row, email in await list_invite_codes()}
    assert by_label["listbatch-001"][1] == customer.email
    assert by_label["listbatch-003"][0].note == "Sarah"

    consumed_labels = {row.label for row, _ in await list_invite_codes("consumed")}
    assert "listbatch-001" in consumed_labels
    assert "listbatch-002" not in consumed_labels

    # Other tests revoke codes too, so only assert about this batch.
    revoked_labels = {row.label for row, _ in await list_invite_codes("revoked")}
    assert "listbatch-002" in revoked_labels
    assert "listbatch-003" not in revoked_labels

    active_labels = {row.label for row, _ in await list_invite_codes("active")}
    assert "listbatch-003" in active_labels
    assert "listbatch-001" not in active_labels
    assert "listbatch-002" not in active_labels
