# tests/test_crud_event_log.py
# Round-trip tests for backend.database.event_log.
#
# Like completion_log, event_log is a write-mostly history table. The
# main thing to test: the event_type CHECK constraint rejects bad values.

import pytest
import sqlite3

from backend.database.event_log import (
    delete_event,
    get_event,
    list_events,
    log_event,
    update_event,
)
from backend.database.tasks import create_task


# ========== Create + Read ==========


def test_log_and_get_event(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_event(conn, id="e1", task_id="t1", event_type="scheduled",
              old_value=None, new_value="b1", reason="AI planning")
    row = get_event(conn, "e1")
    assert row is not None
    assert row["event_type"] == "scheduled"
    assert row["new_value"] == "b1"
    assert row["reason"] == "AI planning"
    assert row["created_at"] is not None  # schema default


def test_log_event_optional_fields_default_to_null(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_event(conn, id="e1", task_id="t1", event_type="scheduled")
    row = get_event(conn, "e1")
    assert row["old_value"] is None
    assert row["new_value"] is None
    assert row["reason"] is None


def test_log_event_rejects_unknown_event_type(conn):
    """
    The schema has a CHECK constraint on event_type. SQLite enforces it,
    so log_event must propagate the IntegrityError.
    """
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    with pytest.raises(sqlite3.IntegrityError):
        log_event(conn, id="e1", task_id="t1", event_type="bogus_event")


def test_log_event_accepts_all_six_event_types(conn):
    """
    The CHECK constraint allows exactly six event types. Smoke-check
    that all of them write successfully.
    """
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    for i, et in enumerate(
        ["scheduled", "rescheduled", "status_change",
         "completed", "cancelled", "manually_moved"]
    ):
        log_event(conn, id=f"e{i}", task_id="t1", event_type=et)


# ========== List + filters ==========


def test_list_events_orders_by_created_at_desc(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_event(conn, id="e1", task_id="t1", event_type="scheduled",
              created_at="2026-01-01T10:00:00.000Z") if False else log_event(
        conn, id="e1", task_id="t1", event_type="scheduled"
    )
    # Two events, the newer one must come first
    import time; time.sleep(0.01)
    log_event(conn, id="e2", task_id="t1", event_type="rescheduled")
    rows = list_events(conn)
    assert [r["id"] for r in rows] == ["e2", "e1"]


def test_list_events_filter_by_task_id(conn):
    create_task(conn, id="t1", title="a", estimated_duration_minutes=10)
    create_task(conn, id="t2", title="b", estimated_duration_minutes=10)
    log_event(conn, id="e1", task_id="t1", event_type="scheduled")
    log_event(conn, id="e2", task_id="t2", event_type="scheduled")
    rows = list_events(conn, task_id="t1")
    assert [r["id"] for r in rows] == ["e1"]


def test_list_events_filter_by_event_type(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_event(conn, id="e1", task_id="t1", event_type="scheduled")
    log_event(conn, id="e2", task_id="t1", event_type="rescheduled")
    rows = list_events(conn, event_type="scheduled")
    assert [r["id"] for r in rows] == ["e1"]


def test_list_events_filter_by_since(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_event(conn, id="e1", task_id="t1", event_type="scheduled")
    import time; time.sleep(0.01)
    log_event(conn, id="e2", task_id="t1", event_type="scheduled")
    rows = list_events(conn, since="9999-12-31T00:00:00.000Z")
    assert rows == []  # future timestamp, nothing matches


# ========== Update + Delete ==========


def test_update_event(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_event(conn, id="e1", task_id="t1", event_type="scheduled")
    update_event(conn, "e1", reason="corrected reason")
    assert get_event(conn, "e1")["reason"] == "corrected reason"


def test_update_event_raises_on_empty(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_event(conn, id="e1", task_id="t1", event_type="scheduled")
    with pytest.raises(ValueError):
        update_event(conn, "e1")


def test_delete_event(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_event(conn, id="e1", task_id="t1", event_type="scheduled")
    assert delete_event(conn, "e1") is True
    assert get_event(conn, "e1") is None
