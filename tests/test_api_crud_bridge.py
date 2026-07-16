# tests/test_api_crud_bridge.py
# Tests for the api.py CRUD bridge — one round-trip per table to
# confirm the JS-shaped methods correctly call the underlying CRUD
# functions and return the standard envelope.
#
# These tests are the integration test: api.createTask(...) →
# api.getTask(...) → assert the data round-trips. They prove the
# kwargs forwarding, the envelope, and the connection lifecycle all
# work together.

import pytest
import sqlite3

from backend import database
from backend.database.tasks import create_task


# ========== Tasks ==========


def test_api_task_round_trip(api):
    res = api.createTask({
        "id": "t1", "title": "Write plan",
        "estimated_duration_minutes": 30, "priority": 2,
    })
    assert res["ok"] is True, res

    got = api.getTask("t1")
    assert got["ok"] is True
    assert got["data"]["title"] == "Write plan"
    assert got["data"]["priority"] == 2


def test_api_updateTask_changes_field(api):
    api.createTask({"id": "t1", "title": "a", "estimated_duration_minutes": 10})
    res = api.updateTask("t1", {"title": "b"})
    assert res["ok"] is True
    assert api.getTask("t1")["data"]["title"] == "b"


def test_api_deleteTask_removes_row(api):
    api.createTask({"id": "t1", "title": "a", "estimated_duration_minutes": 10})
    res = api.deleteTask("t1")
    assert res["ok"] is True
    # getTask on a missing id returns the success envelope with data=None.
    assert api.getTask("t1") == {"ok": True, "data": None}


def test_api_listTasks_with_status_filter(api):
    api.createTask({"id": "t1", "title": "a", "estimated_duration_minutes": 10,
                    "status": "pending"})
    api.createTask({"id": "t2", "title": "b", "estimated_duration_minutes": 10,
                    "status": "completed"})
    res = api.listTasks(status="pending")
    assert res["ok"] is True
    assert [r["id"] for r in res["data"]] == ["t1"]


# ========== Fixed events ==========


def test_api_fixed_event_round_trip(api):
    api.createFixedEvent({
        "id": "f1", "title": "Standup",
        "start_time": "2026-01-01T09:00:00.000Z",
        "end_time": "2026-01-01T09:30:00.000Z",
    })
    got = api.getFixedEvent("f1")
    assert got["ok"] is True
    assert got["data"]["title"] == "Standup"


# ========== Schedule blocks ==========


def test_api_schedule_block_round_trip(api):
    api.createTask({"id": "t1", "title": "t", "estimated_duration_minutes": 10})
    api.createScheduleBlock({
        "id": "b1", "task_id": "t1",
        "start_time": "2026-01-01T10:00:00.000Z",
        "end_time": "2026-01-01T10:30:00.000Z",
    })
    got = api.getScheduleBlock("b1")
    assert got["ok"] is True
    assert got["data"]["status"] == "planned"


# ========== Completion log ==========


def test_api_log_completion_round_trip(api):
    api.createTask({"id": "t1", "title": "t", "estimated_duration_minutes": 10})
    api.logCompletion({
        "id": "c1", "task_id": "t1",
        "completed_at": "2026-01-01T11:00:00.000Z",
        "actual_duration_minutes": 12, "planned_duration_minutes": 10,
        "topic": "work", "start_time": "2026-01-01T10:00:00.000Z",
    })
    got = api.getCompletion("c1")
    assert got["ok"] is True
    assert got["data"]["actual_duration_minutes"] == 12


# ========== Productivity ==========


def test_api_upsert_productivity_round_trip(api):
    res = api.upsertProductivity(1, 9, 1.5)
    assert res["ok"] is True
    got = api.getProductivity(1, 9)
    assert got["ok"] is True
    assert got["data"]["efficiency_score"] == 1.5


# ========== Topic efficiency ==========


def test_api_upsert_topic_efficiency_round_trip(api):
    res = api.upsertTopicEfficiency("work", 0.8)
    assert res["ok"] is True
    got = api.getTopicEfficiency("work")
    assert got["ok"] is True
    assert got["data"]["efficiency_multiplier"] == 0.8


# ========== Event log ==========


def test_api_log_event_round_trip(api):
    api.createTask({"id": "t1", "title": "t", "estimated_duration_minutes": 10})
    api.logEvent({
        "id": "e1", "task_id": "t1", "event_type": "scheduled",
        "new_value": "b1",
    })
    got = api.getEvent("e1")
    assert got["ok"] is True
    assert got["data"]["event_type"] == "scheduled"


# ========== Kwargs forwarding ==========


def test_api_createTask_ignores_unknown_keys(api):
    """
    api.createTask passes the payload as **kwargs. Unknown keys should
    raise TypeError (caught and turned into an error envelope), not
    silently succeed with a half-written row.
    """
    res = api.createTask({
        "id": "t1", "title": "x", "estimated_duration_minutes": 10,
        "this_key_does_not_exist": 42,
    })
    assert res["ok"] is False
    assert "error" in res
