"""Checkpointer factory — SQLite in dev, Postgres in prod.

Usage (in FastAPI lifespan):

    async with make_checkpointer() as cp:
        graph = builder.compile(checkpointer=cp)
        yield
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./car_agent.db")


@asynccontextmanager
async def make_checkpointer() -> AsyncGenerator:
    if DATABASE_URL.startswith("postgresql"):
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        # Strip the SQLAlchemy driver prefix so psycopg/asyncpg can parse it.
        pg_url = (
            DATABASE_URL
            .replace("postgresql+asyncpg://", "postgresql://")
            .replace("postgresql+psycopg://", "postgresql://")
        )
        async with AsyncPostgresSaver.from_conn_string(pg_url) as cp:
            await cp.setup()
            yield cp
    else:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        # Strip the SQLAlchemy driver prefix to get a plain file path.
        db_path = (
            DATABASE_URL
            .replace("sqlite+aiosqlite:///", "")
            .lstrip("./")
        )
        db_path = db_path or "car_agent.db"
        async with AsyncSqliteSaver.from_conn_string(db_path) as cp:
            await cp.setup()
            yield cp
