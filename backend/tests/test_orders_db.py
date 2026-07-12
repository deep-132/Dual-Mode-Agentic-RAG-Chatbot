import sqlite3

import pytest

from app.sql.db import OrdersRepository, _readonly_connection, build_orders_db


@pytest.fixture()
def orders_db(tmp_path):
    csv_path = tmp_path / "orders.csv"
    csv_path.write_text(
        "order_id,customer,product,amount,status,order_date\n"
        "ORD-1,Alice,Widget,100,delivered,2026-01-01\n"
        "ORD-2,Bob,Gadget,200,pending,2026-05-01\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "orders.db"
    build_orders_db(csv_path, db_path)
    return db_path


def test_repository_runs_valid_select(orders_db):
    repo = OrdersRepository(orders_db, row_limit=200)
    result = repo.run_query("SELECT * FROM orders WHERE status = 'pending'")
    assert result.error is None
    assert result.row_count == 1
    assert result.rows[0]["order_id"] == "ORD-2"


def test_repository_rejects_invalid_sql_before_hitting_db(orders_db):
    repo = OrdersRepository(orders_db, row_limit=200)
    result = repo.run_query("DELETE FROM orders")
    assert result.error is not None
    assert result.row_count == 0


def test_engine_level_query_only_blocks_writes_even_if_guard_is_bypassed(orders_db):
    """Belt-and-suspenders check: even calling sqlite3 directly against the
    read-only connection (i.e. simulating the guard being skipped entirely)
    must fail, because PRAGMA query_only is engine-enforced."""
    conn = _readonly_connection(orders_db)
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM orders")
    finally:
        conn.close()
