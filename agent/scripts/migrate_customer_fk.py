"""One-shot migration: replace customer_email columns with customer_id FKs.

Run once: `cd agent && uv run python -m scripts.migrate_customer_fk`.

What it does:
  1. Detects whether the old schema is present. Idempotent: exits early if
     migration has already been applied.
  2. Collects every distinct email from `orders.customer_email`,
     `search_results.email`, and `review_checkpoints.customer_email`.
  3. Creates a `customers` row (UUID PK) per distinct email if not present.
  4. Rebuilds each affected table with the new schema (UUID FK, no email
     column) using SQLite's table-rebuild pattern, mapping email -> customer_id
     during the copy.
  5. The new auth tables (`customer_sessions`, `auth_otps`) and the
     `customers` table itself are created/altered by `init_db()` on the next
     app startup; this script doesn't touch them directly.

Empty tables (`searches`, `negotiations`, `listings`, `messages`,
`negotiation_threads`, `customers`) are dropped and will be recreated by
`init_db()`. This avoids needing to migrate their `customer_id` column type
(int -> String) when there's nothing to preserve.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()

# Force a sync SQLite URL since this script runs DDL synchronously.
DB_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./car_agent.db")
SYNC_URL = DB_URL.replace("+aiosqlite", "")

import sqlalchemy as sa
from sqlalchemy import create_engine, inspect, text

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


EMPTY_TABLES_TO_DROP = [
    # Order matters: drop dependents before parents.
    "messages",
    "negotiation_threads",
    "negotiations",
    "listings",
    "searches",
    "customers",
]


def _table_has_column(conn, table: str, column: str) -> bool:
    insp = inspect(conn)
    if table not in insp.get_table_names():
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def _drop_empty_legacy_tables(conn) -> None:
    insp = inspect(conn)
    existing = set(insp.get_table_names())
    for t in EMPTY_TABLES_TO_DROP:
        if t in existing:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar() or 0
            if count > 0:
                logger.warning("Skipping drop of non-empty table %s (%d rows)", t, count)
                continue
            logger.info("Dropping empty legacy table %s", t)
            conn.execute(text(f"DROP TABLE {t}"))


def _build_email_to_customer_map(conn) -> dict[str, str]:
    """Collect all distinct emails from the three legacy tables and create
    a customers row for each (UUID PK)."""
    emails: set[str] = set()
    if _table_has_column(conn, "orders", "customer_email"):
        for (e,) in conn.execute(text("SELECT DISTINCT customer_email FROM orders WHERE customer_email IS NOT NULL")):
            emails.add(e)
    if _table_has_column(conn, "search_results", "email"):
        for (e,) in conn.execute(text("SELECT DISTINCT email FROM search_results WHERE email IS NOT NULL")):
            emails.add(e)
    if _table_has_column(conn, "review_checkpoints", "customer_email"):
        for (e,) in conn.execute(text("SELECT DISTINCT customer_email FROM review_checkpoints WHERE customer_email IS NOT NULL")):
            emails.add(e)

    logger.info("Found %d distinct emails to backfill", len(emails))

    # Recreate customers fresh with the new UUID schema. Empty-table drop
    # already removed the old int-PK customers table.
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS customers (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(200),
            email VARCHAR(200) NOT NULL UNIQUE,
            phone VARCHAR(50),
            created_at DATETIME NOT NULL
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_customers_email ON customers(email)"))

    email_to_id: dict[str, str] = {}
    for email in emails:
        existing = conn.execute(
            text("SELECT id FROM customers WHERE email = :e"),
            {"e": email},
        ).scalar()
        if existing:
            email_to_id[email] = existing
            continue
        cid = str(uuid4())
        conn.execute(
            text(
                "INSERT INTO customers (id, email, created_at) "
                "VALUES (:id, :email, CURRENT_TIMESTAMP)"
            ),
            {"id": cid, "email": email},
        )
        email_to_id[email] = cid
    return email_to_id


def _migrate_orders(conn, email_to_id: dict[str, str]) -> None:
    if not _table_has_column(conn, "orders", "customer_email"):
        logger.info("orders: already migrated")
        return
    logger.info("orders: rebuilding with customer_id FK")
    conn.execute(text("""
        CREATE TABLE orders__new (
            uuid VARCHAR(36) PRIMARY KEY,
            search_result_id VARCHAR(36) REFERENCES search_results(uuid),
            customer_id VARCHAR(36) NOT NULL REFERENCES customers(id),
            car_info JSON NOT NULL,
            selected_listings JSON NOT NULL,
            need_by_date DATETIME NOT NULL,
            payment_method VARCHAR(20) NOT NULL,
            delivery_method VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'submitted',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
    """))
    rows = conn.execute(text("""
        SELECT uuid, search_result_id, customer_email, car_info, selected_listings,
               need_by_date, payment_method, delivery_method, status, created_at, updated_at
        FROM orders
    """)).all()
    for r in rows:
        cid = email_to_id.get(r.customer_email)
        if cid is None:
            logger.warning("orders: row %s has unknown email %s — skipping", r.uuid, r.customer_email)
            continue
        conn.execute(text("""
            INSERT INTO orders__new
              (uuid, search_result_id, customer_id, car_info, selected_listings,
               need_by_date, payment_method, delivery_method, status, created_at, updated_at)
            VALUES
              (:uuid, :sri, :cid, :ci, :sl, :nb, :pm, :dm, :st, :ca, :ua)
        """), {
            "uuid": r.uuid, "sri": r.search_result_id, "cid": cid,
            "ci": r.car_info, "sl": r.selected_listings,
            "nb": r.need_by_date, "pm": r.payment_method, "dm": r.delivery_method,
            "st": r.status, "ca": r.created_at, "ua": r.updated_at,
        })
    conn.execute(text("DROP TABLE orders"))
    conn.execute(text("ALTER TABLE orders__new RENAME TO orders"))
    conn.execute(text("CREATE INDEX ix_orders_customer_id ON orders(customer_id)"))
    logger.info("orders: rebuilt (%d rows)", len(rows))


def _migrate_search_results(conn, email_to_id: dict[str, str]) -> None:
    if not _table_has_column(conn, "search_results", "email"):
        logger.info("search_results: already migrated")
        return
    logger.info("search_results: rebuilding with customer_id FK")
    conn.execute(text("""
        CREATE TABLE search_results__new (
            uuid VARCHAR(36) PRIMARY KEY,
            customer_id VARCHAR(36) NOT NULL REFERENCES customers(id),
            car_info JSON NOT NULL,
            listings JSON NOT NULL,
            num_found INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            created_at DATETIME NOT NULL
        )
    """))
    rows = conn.execute(text("""
        SELECT uuid, email, car_info, listings, num_found, status, created_at
        FROM search_results
    """)).all()
    for r in rows:
        cid = email_to_id.get(r.email)
        if cid is None:
            logger.warning("search_results: row %s has unknown email %s — skipping", r.uuid, r.email)
            continue
        conn.execute(text("""
            INSERT INTO search_results__new
              (uuid, customer_id, car_info, listings, num_found, status, created_at)
            VALUES (:uuid, :cid, :ci, :ls, :nf, :st, :ca)
        """), {
            "uuid": r.uuid, "cid": cid, "ci": r.car_info, "ls": r.listings,
            "nf": r.num_found, "st": r.status, "ca": r.created_at,
        })
    conn.execute(text("DROP TABLE search_results"))
    conn.execute(text("ALTER TABLE search_results__new RENAME TO search_results"))
    conn.execute(text("CREATE INDEX ix_search_results_customer_id ON search_results(customer_id)"))
    logger.info("search_results: rebuilt (%d rows)", len(rows))


def _migrate_review_checkpoints(conn, email_to_id: dict[str, str]) -> None:
    if not _table_has_column(conn, "review_checkpoints", "customer_email"):
        logger.info("review_checkpoints: already migrated")
        return
    logger.info("review_checkpoints: rebuilding with customer_id FK")
    conn.execute(text("""
        CREATE TABLE review_checkpoints__new (
            id VARCHAR(36) PRIMARY KEY,
            kind VARCHAR(30) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            search_result_id VARCHAR(36) REFERENCES search_results(uuid),
            customer_id VARCHAR(36) NOT NULL REFERENCES customers(id),
            title VARCHAR(200) NOT NULL,
            payload JSON NOT NULL,
            result JSON,
            actor VARCHAR(200),
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            acted_at DATETIME
        )
    """))
    rows = conn.execute(text("""
        SELECT id, kind, status, search_result_id, customer_email, title,
               payload, result, actor, created_at, updated_at, acted_at
        FROM review_checkpoints
    """)).all()
    for r in rows:
        cid = email_to_id.get(r.customer_email)
        if cid is None:
            logger.warning("review_checkpoints: row %s has unknown email %s — skipping", r.id, r.customer_email)
            continue
        conn.execute(text("""
            INSERT INTO review_checkpoints__new
              (id, kind, status, search_result_id, customer_id, title,
               payload, result, actor, created_at, updated_at, acted_at)
            VALUES (:id, :k, :st, :sri, :cid, :ti, :pl, :rs, :ac, :ca, :ua, :aa)
        """), {
            "id": r.id, "k": r.kind, "st": r.status, "sri": r.search_result_id,
            "cid": cid, "ti": r.title, "pl": r.payload, "rs": r.result,
            "ac": r.actor, "ca": r.created_at, "ua": r.updated_at, "aa": r.acted_at,
        })
    conn.execute(text("DROP TABLE review_checkpoints"))
    conn.execute(text("ALTER TABLE review_checkpoints__new RENAME TO review_checkpoints"))
    conn.execute(text("CREATE INDEX ix_review_checkpoints_kind ON review_checkpoints(kind)"))
    conn.execute(text("CREATE INDEX ix_review_checkpoints_status ON review_checkpoints(status)"))
    conn.execute(text("CREATE INDEX ix_review_checkpoints_search_result_id ON review_checkpoints(search_result_id)"))
    conn.execute(text("CREATE INDEX ix_review_checkpoints_customer_id ON review_checkpoints(customer_id)"))
    conn.execute(text("CREATE INDEX ix_review_checkpoints_status_created ON review_checkpoints(status, created_at)"))
    logger.info("review_checkpoints: rebuilt (%d rows)", len(rows))


def main() -> int:
    logger.info("Migrating %s", SYNC_URL)
    engine = create_engine(SYNC_URL)
    with engine.begin() as conn:
        # SQLite-only safety: temporarily disable FK checks during rebuilds.
        conn.execute(text("PRAGMA foreign_keys = OFF"))
        _drop_empty_legacy_tables(conn)
        email_to_id = _build_email_to_customer_map(conn)
        _migrate_orders(conn, email_to_id)
        _migrate_search_results(conn, email_to_id)
        _migrate_review_checkpoints(conn, email_to_id)
        conn.execute(text("PRAGMA foreign_keys = ON"))
    logger.info("Migration complete. Run the app to let init_db() create remaining tables.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
