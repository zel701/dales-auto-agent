"""Shared pytest fixtures."""

from __future__ import annotations

import os

# Must be set before any car_agent imports so the engine picks up the test URL.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_car_agent.db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import pytest


@pytest.fixture(scope="session", autouse=True)
async def init_test_db():
    from car_agent.db.database import init_db

    await init_db()
    yield
    try:
        os.remove("./test_car_agent.db")
    except FileNotFoundError:
        pass
