# tests/test_crud_topic_efficiency.py
# Round-trip tests for backend.database.topic_efficiency.
#
# user_topic_efficiency has a string PK (topic) and one write operation:
# upsert. The upsert also bumps `last_updated` automatically.

import time

from backend.database.topic_efficiency import (
    delete_topic_efficiency,
    get_topic_efficiency,
    list_topic_efficiencies,
    upsert_topic_efficiency,
)


# ========== Upsert + Get ==========


def test_upsert_creates_new_topic(conn):
    upsert_topic_efficiency(conn, topic="work", efficiency_multiplier=0.8)
    row = get_topic_efficiency(conn, "work")
    assert row is not None
    assert row["efficiency_multiplier"] == 0.8


def test_upsert_overwrites_existing_topic(conn):
    upsert_topic_efficiency(conn, topic="work", efficiency_multiplier=0.8)
    upsert_topic_efficiency(conn, topic="work", efficiency_multiplier=1.2)
    row = get_topic_efficiency(conn, "work")
    assert row["efficiency_multiplier"] == 1.2


def test_upsert_bumps_last_updated(conn):
    """
    Unlike most tables, topic_efficiency's upsert sets last_updated to
    the current strftime time. Verify that two upserts in a row produce
    different timestamps.
    """
    upsert_topic_efficiency(conn, topic="work", efficiency_multiplier=0.8)
    first = get_topic_efficiency(conn, "work")["last_updated"]
    time.sleep(0.01)
    upsert_topic_efficiency(conn, topic="work", efficiency_multiplier=0.9)
    second = get_topic_efficiency(conn, "work")["last_updated"]
    assert second > first


def test_get_topic_efficiency_returns_none_for_missing(conn):
    assert get_topic_efficiency(conn, "ghost") is None


# ========== List ==========


def test_list_topic_efficiencies_orders_by_topic(conn):
    upsert_topic_efficiency(conn, topic="work", efficiency_multiplier=0.8)
    upsert_topic_efficiency(conn, topic="admin", efficiency_multiplier=1.0)
    upsert_topic_efficiency(conn, topic="study", efficiency_multiplier=0.6)
    rows = list_topic_efficiencies(conn)
    assert [r["topic"] for r in rows] == ["admin", "study", "work"]


# ========== Delete ==========


def test_delete_topic_efficiency_removes_row(conn):
    upsert_topic_efficiency(conn, topic="work", efficiency_multiplier=0.8)
    assert delete_topic_efficiency(conn, "work") is True
    assert get_topic_efficiency(conn, "work") is None


def test_delete_topic_efficiency_returns_false_when_missing(conn):
    assert delete_topic_efficiency(conn, "ghost") is False
