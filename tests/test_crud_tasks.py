# tests/test_crud_tasks.py
# Round-trip tests for backend.database.tasks.
#
# tasks is the "intent" table — the centerpiece. We test:
#   * create + get round-trip
#   * defaults (status, priority, timestamps)
#   * list with filters (status, topic, limit)
#   * update bumps updated_at (and rejects modifying created_at)
#   * delete (and the cascade-blocking behavior covered in schedule_blocks)

import time

import pytest
import sqlite3

from backend.database.tasks import (
    create_task,
    delete_task,
    get_task,
    list_tasks,
    update_task,
)


# ========== Create + Read ==========


def test_create_and_get_task(conn):
    create_task(conn, id="t1", title="Write plan", estimated_duration_minutes=30)
    row = get_task(conn, "t1")
    assert row is not None
    assert row["title"] == "Write plan"
    assert row["estimated_duration_minutes"] == 30
    assert row["id"] == "t1"


def test_create_task_uses_default_status_pending(conn):
    """New tasks default to status='pending' per the schema."""
    create_task(conn, id="t1", title="x", estimated_duration_minutes=10)
    assert get_task(conn, "t1")["status"] == "pending"


def test_create_task_uses_default_priority_three(conn):
    """Default priority is 3 (middle of 1..5)."""
    create_task(conn, id="t1", title="x", estimated_duration_minutes=10)
    assert get_task(conn, "t1")["priority"] == 3


def test_create_task_populates_timestamps(conn):
    """created_at and updated_at are set by SQLite's strftime default."""
    create_task(conn, id="t1", title="x", estimated_duration_minutes=10)
    row = get_task(conn, "t1")
    assert row["created_at"] is not None
    assert row["updated_at"] is not None
    assert row["created_at"].endswith("Z")
    assert row["updated_at"].endswith("Z")


def test_create_task_optional_fields_default_to_null(conn):
    """deadline, earliest_start, topic, recurrence_rule default to NULL."""
    create_task(conn, id="t1", title="x", estimated_duration_minutes=10)
    row = get_task(conn, "t1")
    assert row["deadline"] is None
    assert row["earliest_start"] is None
    assert row["topic"] is None
    assert row["recurrence_rule"] is None


def test_create_task_coerces_empty_string_to_null(conn):
    """coerce_filter_value collapses '' to None — verify it flows through."""
    create_task(
        conn, id="t1", title="x", estimated_duration_minutes=10,
        deadline="", topic="", recurrence_rule="",
    )
    row = get_task(conn, "t1")
    assert row["deadline"] is None
    assert row["topic"] is None
    assert row["recurrence_rule"] is None


def test_get_task_returns_none_for_missing_id(conn):
    """A non-existent id should return None, not raise."""
    assert get_task(conn, "ghost") is None


def test_create_task_duplicate_id_raises(conn):
    """Primary key on id — inserting a duplicate must raise IntegrityError."""
    create_task(conn, id="t1", title="x", estimated_duration_minutes=10)
    with pytest.raises(sqlite3.IntegrityError):
        create_task(conn, id="t1", title="y", estimated_duration_minutes=5)


# ========== List + filters ==========


def test_list_tasks_empty(conn):
    """Empty DB → empty list, not None, not an exception."""
    assert list_tasks(conn) == []


def test_list_tasks_returns_all_in_descending_created_order(conn):
    """Newer tasks come first; this is the default ordering."""
    create_task(conn, id="t1", title="first", estimated_duration_minutes=10)
    # Sleep is not needed because the millisecond timestamp from strftime
    # is monotonic per row, but a tiny wait keeps the test stable.
    time.sleep(0.01)
    create_task(conn, id="t2", title="second", estimated_duration_minutes=10)
    rows = list_tasks(conn)
    assert [r["id"] for r in rows] == ["t2", "t1"]


def test_list_tasks_filter_by_status(conn):
    create_task(conn, id="t1", title="a", estimated_duration_minutes=10, status="pending")
    create_task(conn, id="t2", title="b", estimated_duration_minutes=10, status="completed")
    rows = list_tasks(conn, status="pending")
    assert len(rows) == 1
    assert rows[0]["id"] == "t1"


def test_list_tasks_filter_by_topic(conn):
    create_task(conn, id="t1", title="a", estimated_duration_minutes=10, topic="work")
    create_task(conn, id="t2", title="b", estimated_duration_minutes=10, topic="study")
    rows = list_tasks(conn, topic="work")
    assert len(rows) == 1
    assert rows[0]["id"] == "t1"


def test_list_tasks_limit(conn):
    for i in range(5):
        create_task(conn, id=f"t{i}", title=f"task {i}", estimated_duration_minutes=10)
    rows = list_tasks(conn, limit=2)
    assert len(rows) == 2


def test_list_tasks_combined_filters(conn):
    """status + topic together: only rows matching both come back."""
    create_task(conn, id="t1", title="a", estimated_duration_minutes=10,
                status="pending", topic="work")
    create_task(conn, id="t2", title="b", estimated_duration_minutes=10,
                status="completed", topic="work")
    create_task(conn, id="t3", title="c", estimated_duration_minutes=10,
                status="pending", topic="study")
    rows = list_tasks(conn, status="pending", topic="work")
    assert [r["id"] for r in rows] == ["t1"]


# ========== Update ==========


def test_update_task_changes_field(conn):
    create_task(conn, id="t1", title="a", estimated_duration_minutes=10)
    update_task(conn, "t1", title="b")
    assert get_task(conn, "t1")["title"] == "b"


def test_update_task_bumps_updated_at(conn):
    """
    Every successful update must move updated_at forward. The schema's
    default and the helper's strftime give millisecond precision, so a
    brief sleep guarantees we see a different value.
    """
    create_task(conn, id="t1", title="a", estimated_duration_minutes=10)
    before = get_task(conn, "t1")["updated_at"]
    time.sleep(0.01)
    update_task(conn, "t1", title="b")
    after = get_task(conn, "t1")["updated_at"]
    assert after > before


def test_update_task_returns_false_for_missing_id(conn):
    """No row matches → rowcount is 0 → returns False, not None."""
    assert update_task(conn, "ghost", title="x") is False


def test_update_task_rejects_modifying_created_at(conn):
    """
    created_at is a SQLite default; letting callers write it would
    corrupt the audit trail. Lock that in with a ValueError.
    """
    create_task(conn, id="t1", title="a", estimated_duration_minutes=10)
    with pytest.raises(ValueError, match="created_at"):
        update_task(conn, "t1", created_at="1970-01-01T00:00:00.000Z")


def test_update_task_multiple_fields_at_once(conn):
    create_task(conn, id="t1", title="a", estimated_duration_minutes=10, priority=3)
    update_task(conn, "t1", title="b", priority=5, status="in_progress")
    row = get_task(conn, "t1")
    assert row["title"] == "b"
    assert row["priority"] == 5
    assert row["status"] == "in_progress"


# ========== Delete ==========


def test_delete_task_returns_true_when_row_existed(conn):
    create_task(conn, id="t1", title="a", estimated_duration_minutes=10)
    assert delete_task(conn, "t1") is True
    assert get_task(conn, "t1") is None


def test_delete_task_returns_false_when_row_missing(conn):
    assert delete_task(conn, "ghost") is False
