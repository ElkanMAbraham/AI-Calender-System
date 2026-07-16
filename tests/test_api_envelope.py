# tests/test_api_envelope.py
# Tests for the api.py response envelope: {"ok": True, "data": ...} on
# success and {"ok": False, "error": str} on failure.
#
# Every method on the Api class is supposed to return one of these two
# shapes. We don't need to test the body of every method here — that's
# what test_api_crud_bridge.py is for — but we DO test the envelope for
# a representative sample, plus the explicit error paths (missing rows,
# FK violations) so we know the envelope wraps exceptions correctly.

import pytest
import sqlite3

from backend import database
from backend.database.tasks import create_task, delete_task


# ========== Envelope shape on happy paths ==========


def test_listTasks_envelope(api):
    res = api.listTasks()
    assert res["ok"] is True
    assert isinstance(res["data"], list)


def test_listFixedEvents_envelope(api):
    res = api.listFixedEvents()
    assert res["ok"] is True
    assert isinstance(res["data"], list)


def test_listScheduleBlocks_envelope(api):
    res = api.listScheduleBlocks()
    assert res["ok"] is True
    assert isinstance(res["data"], list)


def test_listCompletions_envelope(api):
    res = api.listCompletions()
    assert res["ok"] is True
    assert isinstance(res["data"], list)


def test_listProductivity_envelope(api):
    res = api.listProductivity()
    assert res["ok"] is True
    assert isinstance(res["data"], list)


def test_listTopicEfficiencies_envelope(api):
    res = api.listTopicEfficiencies()
    assert res["ok"] is True
    assert isinstance(res["data"], list)


def test_listEvents_envelope(api):
    res = api.listEvents()
    assert res["ok"] is True
    assert isinstance(res["data"], list)


# ========== Envelope shape on error paths ==========


def test_getTask_missing_returns_data_none(api):
    """
    get_task returns None for a missing id (not an exception), and the
    bridge wraps None in {"ok": True, "data": None}. That's a legitimate
    success shape — JS code checks `data === null` rather than the error
    envelope. Lock that contract in.
    """
    res = api.getTask("ghost-id")
    assert res["ok"] is True
    assert res["data"] is None
    assert "error" not in res


def test_createTask_fk_violation_returns_error_envelope(api):
    """createScheduleBlock with a non-existent task_id must NOT crash JS —
    the bridge must catch the IntegrityError and return the error envelope."""
    res = api.createScheduleBlock({
        "id": "b1", "task_id": "ghost",
        "start_time": "2026-01-01T10:00:00.000Z",
        "end_time": "2026-01-01T10:30:00.000Z",
    })
    assert res["ok"] is False
    assert "error" in res


def test_logCompletion_fk_violation_returns_error_envelope(api):
    """Same for log_completion's task_id FK."""
    res = api.logCompletion({
        "id": "c1", "task_id": "ghost",
        "completed_at": "2026-01-01T11:00:00.000Z",
        "actual_duration_minutes": 10, "planned_duration_minutes": 10,
        "topic": "work", "start_time": "2026-01-01T10:00:00.000Z",
    })
    assert res["ok"] is False
    assert "error" in res


# ========== Envelope structure invariants ==========


def test_envelope_never_returns_both_data_and_error(api):
    """
    Sanity: a response must have either {ok, data} or {ok, error},
    never both. We exercise this by hitting both a success path
    (listTasks on an empty DB) and an error path (FK violation).
    """
    success = api.listTasks()
    assert success["ok"] is True
    assert "data" in success
    assert "error" not in success

    failure = api.createScheduleBlock({
        "id": "b1", "task_id": "ghost",
        "start_time": "2026-01-01T10:00:00.000Z",
        "end_time": "2026-01-01T10:30:00.000Z",
    })
    assert failure["ok"] is False
    assert "error" in failure
    assert "data" not in failure
