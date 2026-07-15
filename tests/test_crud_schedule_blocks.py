# tests/test_crud_schedule_blocks.py
# Round-trip tests for backend.database.schedule_blocks.
#
# The big behaviors to lock in here:
#   * create + get round-trip
#   * is_pinned is stored as INTEGER 0/1 (per the CHECK constraint)
#   * ON DELETE CASCADE from tasks — deleting the task removes its blocks
#   * list with the 4 filters (task_id, status, start_after, end_before)

import pytest
import sqlite3

from backend.database.schedule_blocks import (
    create_schedule_block,
    delete_schedule_block,
    get_schedule_block,
    list_schedule_blocks,
    update_schedule_block,
)
from backend.database.tasks import create_task, delete_task


# ========== Create + Read ==========


def test_create_and_get_block(conn):
    create_task(conn, id="t1", title="task", estimated_duration_minutes=10)
    create_schedule_block(
        conn, id="b1", task_id="t1",
        start_time="2026-01-01T10:00:00.000Z",
        end_time="2026-01-01T10:30:00.000Z",
    )
    row = get_schedule_block(conn, "b1")
    assert row["task_id"] == "t1"
    assert row["status"] == "planned"  # default
    assert row["is_pinned"] == 0       # default (stored as INTEGER)
    assert row["version"] == 1         # default


def test_create_block_is_pinned_stored_as_integer_one(conn):
    """`is_pinned=True` must persist as 1 so the CHECK constraint passes."""
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    create_schedule_block(
        conn, id="b1", task_id="t1",
        start_time="2026-01-01T10:00:00.000Z",
        end_time="2026-01-01T10:30:00.000Z",
        is_pinned=True,
    )
    row = get_schedule_block(conn, "b1")
    assert row["is_pinned"] == 1
    assert row["is_pinned"] is not True  # it's a 0/1 INTEGER, not a Python bool


def test_create_block_optional_fields_default_to_null(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    create_schedule_block(
        conn, id="b1", task_id="t1",
        start_time="2026-01-01T10:00:00.000Z",
        end_time="2026-01-01T10:30:00.000Z",
    )
    row = get_schedule_block(conn, "b1")
    assert row["reasoning"] is None


def test_create_block_fk_violation_raises(conn):
    """task_id must reference an existing task. Missing task → IntegrityError."""
    with pytest.raises(sqlite3.IntegrityError):
        create_schedule_block(
            conn, id="b1", task_id="ghost",
            start_time="2026-01-01T10:00:00.000Z",
            end_time="2026-01-01T10:30:00.000Z",
        )


# ========== List + filters ==========


def test_list_blocks_filter_by_task_id(conn):
    create_task(conn, id="t1", title="a", estimated_duration_minutes=10)
    create_task(conn, id="t2", title="b", estimated_duration_minutes=10)
    create_schedule_block(conn, id="b1", task_id="t1",
                          start_time="2026-01-01T10:00:00.000Z",
                          end_time="2026-01-01T10:30:00.000Z")
    create_schedule_block(conn, id="b2", task_id="t2",
                          start_time="2026-01-01T11:00:00.000Z",
                          end_time="2026-01-01T11:30:00.000Z")
    rows = list_schedule_blocks(conn, task_id="t1")
    assert [r["id"] for r in rows] == ["b1"]


def test_list_blocks_filter_by_status(conn):
    create_task(conn, id="t1", title="a", estimated_duration_minutes=10)
    create_schedule_block(conn, id="b1", task_id="t1",
                          start_time="2026-01-01T10:00:00.000Z",
                          end_time="2026-01-01T10:30:00.000Z",
                          status="planned")
    create_schedule_block(conn, id="b2", task_id="t1",
                          start_time="2026-01-01T11:00:00.000Z",
                          end_time="2026-01-01T11:30:00.000Z",
                          status="cancelled")
    rows = list_schedule_blocks(conn, status="planned")
    assert [r["id"] for r in rows] == ["b1"]


def test_list_blocks_orders_by_start_time(conn):
    create_task(conn, id="t1", title="a", estimated_duration_minutes=10)
    create_schedule_block(conn, id="b2", task_id="t1",
                          start_time="2026-01-01T11:00:00.000Z",
                          end_time="2026-01-01T11:30:00.000Z")
    create_schedule_block(conn, id="b1", task_id="t1",
                          start_time="2026-01-01T10:00:00.000Z",
                          end_time="2026-01-01T10:30:00.000Z")
    rows = list_schedule_blocks(conn)
    assert [r["id"] for r in rows] == ["b1", "b2"]


# ========== Update ==========


def test_update_block_bumps_is_pinned(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    create_schedule_block(conn, id="b1", task_id="t1",
                          start_time="2026-01-01T10:00:00.000Z",
                          end_time="2026-01-01T10:30:00.000Z")
    update_schedule_block(conn, "b1", is_pinned=True)
    assert get_schedule_block(conn, "b1")["is_pinned"] == 1


def test_update_block_rejects_empty_fields(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    create_schedule_block(conn, id="b1", task_id="t1",
                          start_time="2026-01-01T10:00:00.000Z",
                          end_time="2026-01-01T10:30:00.000Z")
    with pytest.raises(ValueError):
        update_schedule_block(conn, "b1")


# ========== Delete ==========


def test_delete_block_returns_true_when_existed(conn):
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    create_schedule_block(conn, id="b1", task_id="t1",
                          start_time="2026-01-01T10:00:00.000Z",
                          end_time="2026-01-01T10:30:00.000Z")
    assert delete_schedule_block(conn, "b1") is True
    assert get_schedule_block(conn, "b1") is None


# ========== Cascade from tasks ==========


def test_deleting_task_cascades_to_blocks(conn):
    """
    schedule_blocks.task_id is ON DELETE CASCADE. Deleting a task
    should silently remove all of its blocks. Lock that in — it's
    a behavior the smoke test missed.
    """
    create_task(conn, id="t1", title="t", estimated_duration_minutes=10)
    create_schedule_block(conn, id="b1", task_id="t1",
                          start_time="2026-01-01T10:00:00.000Z",
                          end_time="2026-01-01T10:30:00.000Z")
    create_schedule_block(conn, id="b2", task_id="t1",
                          start_time="2026-01-01T11:00:00.000Z",
                          end_time="2026-01-01T11:30:00.000Z")

    delete_task(conn, "t1")

    # Both blocks are gone via CASCADE.
    assert get_schedule_block(conn, "b1") is None
    assert get_schedule_block(conn, "b2") is None


def test_deleting_task_does_not_touch_other_tasks_blocks(conn):
    """The cascade is scoped to the deleted task's blocks only."""
    create_task(conn, id="t1", title="a", estimated_duration_minutes=10)
    create_task(conn, id="t2", title="b", estimated_duration_minutes=10)
    create_schedule_block(conn, id="b1", task_id="t1",
                          start_time="2026-01-01T10:00:00.000Z",
                          end_time="2026-01-01T10:30:00.000Z")
    create_schedule_block(conn, id="b2", task_id="t2",
                          start_time="2026-01-01T11:00:00.000Z",
                          end_time="2026-01-01T11:30:00.000Z")

    delete_task(conn, "t1")

    assert get_schedule_block(conn, "b1") is None
    assert get_schedule_block(conn, "b2") is not None  # untouched
