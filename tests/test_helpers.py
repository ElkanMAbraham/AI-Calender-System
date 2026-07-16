# tests/test_helpers.py
# Tests for backend.database._helpers — the small utility module that
# produces timestamps, builds UPDATE SQL, converts rows, and coerces
# filter sentinels.
#
# These are the most "pure-function" tests in the suite — no DB, no
# fixtures beyond what's needed to make a Row.

import sqlite3

from backend.database._helpers import (
    build_update_sql,
    coerce_filter_value,
    now_iso,
    row_to_dict,
)


# ========== now_iso ==========


def test_now_iso_returns_utc_z_suffix():
    """now_iso() must always end in 'Z' so it matches the schema's format."""
    ts = now_iso()
    assert ts.endswith("Z")


def test_now_iso_matches_schema_format():
    """
    Must match strftime('%Y-%m-%dT%H:%M:%fZ', 'now') so timestamps sort
    as strings and round-trip cleanly. That's: 4-digit year, dash,
    2-digit month, 'T' separator, 2-digit hour, etc.
    """
    ts = now_iso()
    # 24 chars: "YYYY-MM-DDTHH:MM:SS.sssZ"
    #                  4 + 1 + 2 + 1 + 2 + 1 + 2 + 1 + 2 + 1 + 2 + 1 + 3 + 1
    assert len(ts) == 24
    # Spot-check the separator positions
    assert ts[4] == "-"
    assert ts[7] == "-"
    assert ts[10] == "T"
    assert ts[13] == ":"
    assert ts[16] == ":"
    assert ts[19] == "."
    assert ts[23] == "Z"


def test_now_iso_is_monotonic_within_a_test():
    """Two calls in quick succession should both produce valid timestamps,
    with the second one >= the first."""
    a = now_iso()
    b = now_iso()
    assert a <= b


# ========== build_update_sql ==========


def test_build_update_sql_basic_set():
    sql, params = build_update_sql("tasks", {"id": "t1", "title": "New"})
    assert "UPDATE tasks SET" in sql
    assert "title = ?" in sql
    assert "updated_at = strftime" in sql
    assert "WHERE id = ?" in sql
    assert params == ["New", "t1"]


def test_build_update_sql_excludes_id_from_set_clause():
    """`id` belongs in the WHERE clause, not the SET clause — otherwise
    we'd be writing back the same value (harmless) or, worse, mismatching
    key/value ordering in the future."""
    sql, _ = build_update_sql("tasks", {"id": "t1", "status": "done"})
    # `id = ?` should not appear in the SET portion
    set_part = sql.split("WHERE")[0]
    assert "id = ?" not in set_part


def test_build_update_sql_raises_on_empty_fields():
    """A no-op UPDATE is almost always a bug — refuse to build it."""
    try:
        build_update_sql("tasks", {})
    except ValueError as e:
        assert "at least one field" in str(e).lower()
    else:
        raise AssertionError("expected ValueError")


def test_build_update_sql_raises_on_missing_id():
    """We need `id` to build the WHERE clause."""
    try:
        build_update_sql("tasks", {"title": "x"})
    except ValueError as e:
        assert "id" in str(e).lower()
    else:
        raise AssertionError("expected ValueError")


def test_build_update_sql_bumps_updated_at():
    """Every UPDATE built by this helper must touch updated_at."""
    sql, _ = build_update_sql("tasks", {"id": "t1", "priority": 1})
    assert "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')" in sql


# ========== coerce_filter_value ==========


def test_coerce_filter_value_none_passes_through():
    """None stays None — the SQL layer treats it as NULL."""
    assert coerce_filter_value(None) is None


def test_coerce_filter_value_empty_string_becomes_none():
    """
    An empty string in a TEXT column is rarely meaningful (especially
    for ISO timestamps or topic tags). We collapse it to None so the
    IS NULL checks in list_filters actually work.
    """
    assert coerce_filter_value("") is None


def test_coerce_filter_value_real_string_passes_through():
    assert coerce_filter_value("work") == "work"


def test_coerce_filter_value_numbers_pass_through():
    """Numbers, bools, etc. are not touched."""
    assert coerce_filter_value(42) == 42
    assert coerce_filter_value(3.14) == 3.14
    assert coerce_filter_value(False) is False


# ========== row_to_dict ==========


def test_row_to_dict_none_passes_through():
    """row_to_dict is called on fetchone() results, which can be None."""
    assert row_to_dict(None) is None


def test_row_to_dict_converts_sqlite_row():
    """A sqlite3.Row should become a plain dict with the same keys/values."""
    # Build a minimal in-memory table so we can fetchone() a real Row.
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE t (a TEXT, b INTEGER)")
    conn.execute("INSERT INTO t VALUES ('x', 1)")
    row = conn.execute("SELECT a, b FROM t").fetchone()

    out = row_to_dict(row)
    assert out == {"a": "x", "b": 1}
    conn.close()
