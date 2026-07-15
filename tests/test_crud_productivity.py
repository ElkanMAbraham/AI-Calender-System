# tests/test_crud_productivity.py
# Round-trip tests for backend.database.productivity.
#
# user_productivity_curve has a composite PK (day_of_week, hour_of_day)
# and only one write operation: upsert. Lock in:
#   * upsert on a fresh cell creates it
#   * upsert on an existing cell overwrites efficiency_score
#   * get / list round-trip
#   * delete works and returns False when the cell is empty

from backend.database.productivity import (
    delete_productivity,
    get_productivity,
    list_productivity,
    upsert_productivity,
)


# ========== Upsert + Get ==========


def test_upsert_creates_new_cell(conn):
    """No prior row → upsert creates one."""
    upsert_productivity(conn, day_of_week=1, hour_of_day=9, efficiency_score=1.5)
    row = get_productivity(conn, day_of_week=1, hour_of_day=9)
    assert row is not None
    assert row["efficiency_score"] == 1.5


def test_upsert_overwrites_existing_cell(conn):
    """Same (day, hour) → efficiency_score is replaced, not duplicated."""
    upsert_productivity(conn, day_of_week=1, hour_of_day=9, efficiency_score=1.5)
    upsert_productivity(conn, day_of_week=1, hour_of_day=9, efficiency_score=0.7)
    row = get_productivity(conn, day_of_week=1, hour_of_day=9)
    assert row["efficiency_score"] == 0.7


def test_get_productivity_returns_none_for_missing_cell(conn):
    assert get_productivity(conn, day_of_week=0, hour_of_day=0) is None


# ========== List ==========


def test_list_productivity_orders_for_heatmap(conn):
    """
    list_productivity should sort day_of_week ASC, hour_of_day ASC so
    the frontend can render a 7x24 grid without resorting.
    """
    upsert_productivity(conn, day_of_week=3, hour_of_day=14, efficiency_score=1.2)
    upsert_productivity(conn, day_of_week=1, hour_of_day=9, efficiency_score=1.5)
    upsert_productivity(conn, day_of_week=1, hour_of_day=8, efficiency_score=0.8)
    rows = list_productivity(conn)
    assert [(r["day_of_week"], r["hour_of_day"]) for r in rows] == [
        (1, 8), (1, 9), (3, 14),
    ]


def test_list_productivity_empty(conn):
    assert list_productivity(conn) == []


# ========== Delete ==========


def test_delete_productivity_removes_cell(conn):
    upsert_productivity(conn, day_of_week=2, hour_of_day=10, efficiency_score=1.0)
    assert delete_productivity(conn, day_of_week=2, hour_of_day=10) is True
    assert get_productivity(conn, day_of_week=2, hour_of_day=10) is None


def test_delete_productivity_returns_false_when_missing(conn):
    assert delete_productivity(conn, day_of_week=6, hour_of_day=23) is False
