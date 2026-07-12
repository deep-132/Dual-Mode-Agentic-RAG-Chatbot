from app.sql.guard import validate_and_sanitize


def test_allows_simple_select():
    result = validate_and_sanitize("SELECT * FROM orders WHERE status = 'pending'", row_limit=200)
    assert result.ok
    assert "LIMIT 200" in result.sanitized_query


def test_preserves_existing_limit():
    result = validate_and_sanitize("SELECT * FROM orders LIMIT 5", row_limit=200)
    assert result.ok
    assert result.sanitized_query.count("LIMIT") == 1
    assert "LIMIT 5" in result.sanitized_query


def test_rejects_non_select():
    result = validate_and_sanitize("DELETE FROM orders", row_limit=200)
    assert not result.ok
    assert "SELECT" in result.error


def test_rejects_multiple_statements():
    result = validate_and_sanitize("SELECT * FROM orders; DROP TABLE orders;", row_limit=200)
    assert not result.ok


def test_rejects_other_tables():
    result = validate_and_sanitize("SELECT * FROM sqlite_master", row_limit=200)
    assert not result.ok
    assert "orders" in result.error


def test_rejects_pragma_and_attach():
    for stmt in ["PRAGMA table_info(orders)", "ATTACH DATABASE 'x' AS y"]:
        result = validate_and_sanitize(stmt, row_limit=200)
        assert not result.ok


def test_rejects_write_disguised_as_select_subquery():
    # A crafted attempt to smuggle a write via a nested clause -- should be
    # caught by the keyword check even though the statement starts with SELECT.
    result = validate_and_sanitize(
        "SELECT * FROM orders WHERE order_id IN (SELECT order_id FROM orders); UPDATE orders SET amount=0",
        row_limit=200,
    )
    assert not result.ok


def test_empty_query_rejected():
    result = validate_and_sanitize("   ", row_limit=200)
    assert not result.ok
