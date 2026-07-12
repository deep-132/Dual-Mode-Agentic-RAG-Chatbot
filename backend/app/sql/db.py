"""Loads orders.csv into a SQLite file once, then serves it via read-only
connections.

Design choice: the on-disk file is opened per-query with `mode=ro` (an
OS-level read-only file handle) *and* `PRAGMA query_only = ON` (an
engine-level read-only mode). Either one alone would stop accidental
writes; both together mean a write attempt is rejected before it can ever
reach disk, regardless of which layer would have caught it. Building once
to a file (rather than keeping one shared in-memory connection alive) also
sidesteps sqlite3's not-thread-safe-by-default connection object -- every
request gets its own short-lived connection instead of contending on one.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from app.schemas import SqlToolResult
from app.sql.guard import validate_and_sanitize

SCHEMA_DESCRIPTION = """\
Table: orders (this is the ONLY table available)
Columns:
  - order_id    TEXT   e.g. 'ORD-1001'
  - customer    TEXT   customer full name
  - product     TEXT   product name, e.g. 'Mechanical Keyboard'
  - amount      REAL   order amount in Indian Rupees (tax-inclusive)
  - status      TEXT   one of: 'pending', 'processing', 'shipped', 'delivered', 'cancelled', 'returned'
  - order_date  TEXT   ISO date 'YYYY-MM-DD', the date the order was placed

Notes:
  - Only SELECT statements against `orders` are permitted; no other tables or statements exist.
  - Do not invent column names. If a question needs a column not listed above, say you don't have that information instead of guessing.
"""


def build_orders_db(csv_path: Path, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE orders (
                order_id   TEXT PRIMARY KEY,
                customer   TEXT NOT NULL,
                product    TEXT NOT NULL,
                amount     REAL NOT NULL,
                status     TEXT NOT NULL,
                order_date TEXT NOT NULL
            )
            """
        )
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [
                (r["order_id"], r["customer"], r["product"], float(r["amount"]), r["status"], r["order_date"])
                for r in reader
            ]
        conn.executemany(
            "INSERT INTO orders (order_id, customer, product, amount, status, order_date) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def _readonly_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
    conn.execute("PRAGMA query_only = ON")
    conn.row_factory = sqlite3.Row
    return conn


class OrdersRepository:
    def __init__(self, db_path: Path, row_limit: int) -> None:
        self._db_path = db_path
        self._row_limit = row_limit

    def run_query(self, sql: str) -> SqlToolResult:
        validation = validate_and_sanitize(sql, self._row_limit)
        if not validation.ok:
            return SqlToolResult(query=sql, row_count=0, rows=[], error=validation.error)

        try:
            conn = _readonly_connection(self._db_path)
            try:
                cursor = conn.execute(validation.sanitized_query)
                rows = [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()
        except sqlite3.Error as exc:
            return SqlToolResult(query=validation.sanitized_query, row_count=0, rows=[], error=str(exc))

        return SqlToolResult(query=validation.sanitized_query, row_count=len(rows), rows=rows)
