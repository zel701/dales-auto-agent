"""One-shot migration: add `orders.credit_score_range`.

Run once per database: `cd agent && uv run python -m scripts.migrate_order_credit_score`.
It targets whatever `DATABASE_URL` points at, so run it against prod's Postgres
as well as any local SQLite file — `init_db()` runs `Base.metadata.create_all`,
which creates missing tables but never adds a column to a table that already
exists, on either backend.

Unlike `migrate_customer_fk.py`, this script runs on the async engine so the one
code path covers aiosqlite and asyncpg alike (there is no sync Postgres driver in
the dependencies).

The column is nullable — cash orders and every row predating the field have no
value — so a plain `ALTER TABLE ... ADD COLUMN` works on both backends; no SQLite
table rebuild is needed. Idempotent: exits early if the column is already there.

`customers.name` and `customers.phone`, which the same intake change now
populates, already exist in the schema and need no migration.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./car_agent.db")

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _redacted(url: str) -> str:
    """Hide the password before logging a Postgres URL."""
    if "@" not in url:
        return url
    scheme, _, rest = url.partition("://")
    creds, _, host = rest.rpartition("@")
    user, _, _ = creds.partition(":")
    return f"{scheme}://{user}:***@{host}" if user else f"{scheme}://***@{host}"


def _table_names(conn) -> list[str]:
    return inspect(conn).get_table_names()


def _column_names(conn, table: str) -> list[str]:
    return [c["name"] for c in inspect(conn).get_columns(table)]


async def main() -> int:
    logger.info("Migrating %s", _redacted(DB_URL))
    engine = create_async_engine(DB_URL)
    try:
        async with engine.begin() as conn:
            tables = await conn.run_sync(_table_names)
            if "orders" not in tables:
                logger.info("orders: table does not exist yet; init_db() will create it")
                return 0
            columns = await conn.run_sync(_column_names, "orders")
            if "credit_score_range" in columns:
                logger.info("orders: credit_score_range already present")
                return 0
            await conn.execute(
                text("ALTER TABLE orders ADD COLUMN credit_score_range VARCHAR(20)")
            )
            logger.info("orders: added credit_score_range")
    finally:
        await engine.dispose()
    logger.info("Migration complete.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
