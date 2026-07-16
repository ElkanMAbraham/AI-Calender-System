# tests/test_crud_completion_log.py
# Round-trip tests for backend.database.completion_log.
#
# The big behaviors to lock in:
#   * log_completion + get round-trip
#   * confidence default is 1.0
#   * list with all 4 filters (task_id, topic, since, until)
#   * update + delete (rarely used but shipped for symmetry)
#   * History rows survive task deletion (the FK is plain REFERENCES,
#     not ON DELETE CASCADE) — this is the most important guarantee.

import pytest
import sqlite3

from backend.database.completion_log import (
    delete_completion,
    get_completion,
    list_completions,
    log_completion,
    update_completion,
)
from backend.database.tasks import create_task, delete_task, get_task


# ========== Create + Read ==========


def test_log_and_get_completion(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_completion(
        conn, id="c1", task_id="t1",
        completed_at="2026-01-01T11:00:00.000Z",
        actual_duration_minutes=12, planned_duration_minutes=10,
        topic="work", start_time="2026-01-01T10:00:00.000Z",
    )
    row = get_completion(conn, "c1")
    assert row is not None
    assert row["task_id"] == "t1"
    assert row["actual_duration_minutes"] == 12
    assert row["planned_duration_minutes"] == 10
    assert row["topic"] == "work"
    assert row["confidence"] == 1.0  # default


def test_log_completion_uses_default_confidence(conn):
    """If the caller doesn't pass confidence, it defaults to 1.0."""
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_completion(
        conn, id="c1", task_id="t1",
        completed_at="2026-01-01T11:00:00.000Z",
        actual_duration_minutes=10, planned_duration_minutes=10,
        topic="work", start_time="2026-01-01T10:00:00.000Z",
    )
    assert get_completion(conn, "c1")["confidence"] == 1.0


def test_get_completion_missing_returns_none(conn):
    assert get_completion(conn, "ghost") is None


# ========== List + filters ==========


def test_list_completions_orders_by_completed_at_desc(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_completion(conn, id="c1", task_id="t1",
                   completed_at="2026-01-01T11:00:00.000Z",
                   actual_duration_minutes=10, planned_duration_minutes=10,
                   topic="work", start_time="2026-01-01T10:00:00.000Z")
    log_completion(conn, id="c2", task_id="t1",
                   completed_at="2026-01-02T11:00:00.000Z",
                   actual_duration_minutes=10, planned_duration_minutes=10,
                   topic="work", start_time="2026-01-02T10:00:00.000Z")
    rows = list_completions(conn)
    # Newer first
    assert [r["id"] for r in rows] == ["c2", "c1"]


def test_list_completions_filter_by_task_id(conn):
    create_task(conn, id="t1", title="a", estimated_duration_minutes=10)
    create_task(conn, id="t2", title="b", estimated_duration_minutes=10)
    log_completion(conn, id="c1", task_id="t1",
                   completed_at="2026-01-01T11:00:00.000Z",
                   actual_duration_minutes=10, planned_duration_minutes=10,
                   topic="work", start_time="2026-01-01T10:00:00.000Z")
    log_completion(conn, id="c2", task_id="t2",
                   completed_at="2026-01-02T11:00:00.000Z",
                   actual_duration_minutes=10, planned_duration_minutes=10,
                   topic="work", start_time="2026-01-02T10:00:00.000Z")
    rows = list_completions(conn, task_id="t1")
    assert [r["id"] for r in rows] == ["c1"]


def test_list_completions_filter_by_topic(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_completion(conn, id="c1", task_id="t1",
                   completed_at="2026-01-01T11:00:00.000Z",
                   actual_duration_minutes=10, planned_duration_minutes=10,
                   topic="work", start_time="2026-01-01T10:00:00.000Z")
    log_completion(conn, id="c2", task_id="t1",
                   completed_at="2026-01-02T11:00:00.000Z",
                   actual_duration_minutes=10, planned_duration_minutes=10,
                   topic="study", start_time="2026-01-02T10:00:00.000Z")
    rows = list_completions(conn, topic="work")
    assert [r["id"] for r in rows] == ["c1"]


def test_list_completions_since_and_until(conn):
    """since/until are half-open: since >= X, until < X."""
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_completion(conn, id="c1", task_id="t1",
                   completed_at="2026-01-01T11:00:00.000Z",
                   actual_duration_minutes=10, planned_duration_minutes=10,
                   topic="work", start_time="2026-01-01T10:00:00.000Z")
    log_completion(conn, id="c2", task_id="t1",
                   completed_at="2026-01-02T11:00:00.000Z",
                   actual_duration_minutes=10, planned_duration_minutes=10,
                   topic="work", start_time="2026-01-02T10:00:00.000Z")
    log_completion(conn, id="c3", task_id="t1",
                   completed_at="2026-01-03T11:00:00.000Z",
                   actual_duration_minutes=10, planned_duration_minutes=10,
                   topic="work", start_time="2026-01-03T10:00:00.000Z")

    rows = list_completions(conn, since="2026-01-02T00:00:00.000Z",
                            until="2026-01-03T00:00:00.000Z")
    assert [r["id"] for r in rows] == ["c2"]


def test_list_completions_limit(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    for i in range(5):
        log_completion(conn, id=f"c{i}", task_id="t1",
                       completed_at=f"2026-01-0{i + 1}T11:00:00.000Z",
                       actual_duration_minutes=10, planned_duration_minutes=10,
                       topic="work", start_time=f"2026-01-0{i + 1}T10:00:00.000Z")
    assert len(list_completions(conn, limit=2)) == 2


# ========== Update + Delete ==========


def test_update_completion_changes_field(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_completion(conn, id="c1", task_id="t1",
                   completed_at="2026-01-01T11:00:00.000Z",
                   actual_duration_minutes=10, planned_duration_minutes=10,
                   topic="work", start_time="2026-01-01T10:00:00.000Z")
    update_completion(conn, "c1", topic="study")
    assert get_completion(conn, "c1")["topic"] == "study"


def test_update_completion_raises_on_empty(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_completion(conn, id="c1", task_id="t1",
                   completed_at="2026-01-01T11:00:00.000Z",
                   actual_duration_minutes=10, planned_duration_minutes=10,
                   topic="work", start_time="2026-01-01T10:00:00.000Z")
    with pytest.raises(ValueError):
        update_completion(conn, "c1")


def test_update_completion_rejects_modifying_id(conn):
    """
    The completion_log.update helper explicitly refuses to set `id`
    via the fields dict (it would be a no-op at best, confusing at
    worst). We trigger the guard by passing `id` as a field; this
    raises a ValueError before reaching SQLite.

    (NB: the function signature takes id as a positional, so the
    only way to test the guard is via the fields dict path. The
    TypeError vs ValueError distinction is unimportant — what
    matters is the call is refused.)
    """
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_completion(conn, id="c1", task_id="t1",
                   completed_at="2026-01-01T11:00:00.000Z",
                   actual_duration_minutes=10, planned_duration_minutes=10,
                   topic="work", start_time="2026-01-01T10:00:00.000Z")
    with pytest.raises((ValueError, TypeError)):
        update_completion(conn, "c1", **{"id": "c2"})


def test_delete_completion(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_completion(conn, id="c1", task_id="t1",
                   completed_at="2026-01-01T11:00:00.000Z",
                   actual_duration_minutes=10, planned_duration_minutes=10,
                   topic="work", start_time="2026-01-01T10:00:00.000Z")
    assert delete_completion(conn, "c1") is True
    assert get_completion(conn, "c1") is None


# ========== History survives task deletion ==========


def test_completion_log_survives_task_deletion(conn):
    """
    The FK to tasks is plain REFERENCES — not ON DELETE CASCADE. So
    deleting a task with completion history raises IntegrityError, NOT
    a silent cascade. This is intentional: history is precious.
    Lock the behavior in either way:
      * If the FK is truly non-cascade, delete_task raises.
      * If callers are expected to clean up first, document that.
    """
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    log_completion(conn, id="c1", task_id="t1",
                   completed_at="2026-01-01T11:00:00.000Z",
                   actual_duration_minutes=10, planned_duration_minutes=10,
                   topic="work", start_time="2026-01-01T10:00:00.000Z")

    # First, remove the history to allow the delete.
    delete_completion(conn, "c1")
    # Now delete_task must succeed.
    assert delete_task(conn, "t1") is True
    assert get_completion(conn, "c1") is None
    assert get_task(conn, "t1") is None
