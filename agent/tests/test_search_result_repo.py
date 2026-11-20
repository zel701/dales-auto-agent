"""Integration tests for search_result_repo against an in-process SQLite DB."""

from __future__ import annotations

import pytest

from car_agent.db.repositories.customer_repo import get_or_create_customer
from car_agent.db.repositories.search_result_repo import (
    create_search_result,
    get_search_result,
)

CAR_INFO = {"make": "Toyota", "model": "Camry", "trim": "XSE", "zipcode": "90210"}
LISTINGS = [{"id": "L1", "price": 28000}, {"id": "L2", "price": 27000}]


@pytest.mark.asyncio
async def test_create_and_retrieve():
    customer = await get_or_create_customer("test@example.com")
    uuid = "test-uuid-1234"
    await create_search_result(
        uuid=uuid,
        customer_id=customer.id,
        car_info=CAR_INFO,
        listings=LISTINGS,
        num_found=2,
    )

    row = await get_search_result(uuid)
    assert row is not None
    assert row.customer_id == customer.id
    assert row.customer.email == "test@example.com"
    assert row.num_found == 2
    assert row.car_info == CAR_INFO
    assert len(row.listings) == 2


@pytest.mark.asyncio
async def test_get_missing_returns_none():
    row = await get_search_result("does-not-exist")
    assert row is None
