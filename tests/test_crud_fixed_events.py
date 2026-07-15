# tests/test_crud_fixed_events.py
# Round-trip tests for backend.database.fixed_events.
#
# fixed_events are immutable in spirit (no updated_at column). We test
# the CRUD surface anyway, since the code exists.

import pytest
import sqlite3

from backend.database.fixed_events import (
    create_fixed_event,
    delete_fixed_event,
    get_fixed_event,
    list_fixed_events,
    update_fixed_event,
)


# ========== Create + Read ==========


def test_create_and_get_fixed_event(conn):
    create_fixed_event(
        conn, id="f1", title="Standup",
        start_time="2026-01-01T09:00:00.000Z",
        end_time="2026-01-01T09:30:00.000Z",
    )
    row = get_fixed_event(conn, "f1")
    assert row["title"] == "Standup"
    assert row["start_time"] == "2026-01-01T09:00:00.000Z"
    assert row["end_time"] == "2026-01-01T09:30:00.000Z"


def test_create_fixed_event_optional_fields_default_to_null(conn):
    create_fixed_event(
        conn, id="f1", title="x",
        start_time="2026-01-01T09:00:00.000Z",
        end_time="2026-01-01T09:30:00.000Z",
    )
    row = get_fixed_event(conn, "f1")
    assert row["recurrence_rule"] is None
    assert row["source"] is None


def test_create_fixed_event_coerces_empty_strings(conn):
    create_fixed_event(
        conn, id="f1", title="x",
        start_time="2026-01-01T09:00:00.000Z",
        end_time="2026-01-01T09:30:00.000Z",
        recurrence_rule="", source="",
    )
    row = get_fixed_event(conn, "f1")
    assert row["recurrence_rule"] is None
    assert row["source"] is None


def test_get_fixed_event_missing_returns_none(conn):
    assert get_fixed_event(conn, "ghost") is None


def test_create_fixed_event_duplicate_id_raises(conn):
    create_fixed_event(
        conn, id="f1", title="x",
        start_time="2026-01-01T09:00:00.000Z",
        end_time="2026-01-01T09:30:00.000Z",
    )
    with pytest.raises(sqlite3.IntegrityError):
        create_fixed_event(
            conn, id="f1", title="y",
            start_time="2026-01-02T09:00:00.000Z",
            end_time="2026-01-02T09:30:00.000Z",
        )


# ========== List + filters ==========


def test_list_fixed_events_orders_by_start_time_asc(conn):
    create_fixed_event(conn, id="f2", title="b", start_time="2026-01-02T09:00:00.000Z",
                       end_time="2026-01-02T09:30:00.000Z")
    create_fixed_event(conn, id="f1", title="a", start_time="2026-01-01T09:00:00.000Z",
                       end_time="2026-01-01T09:30:00.000Z")
    rows = list_fixed_events(conn)
    assert [r["id"] for r in rows] == ["f1", "f2"]


def test_list_fixed_events_start_after_filter(conn):
    """`start_after` translates to `end_time > ?` (overlap, not strict)."""
    create_fixed_event(conn, id="f1", title="a", start_time="2026-01-01T09:00:00.000Z",
                       end_time="2026-01-01T09:30:00.000Z")
    create_fixed_event(conn, id="f2", title="b", start_time="2026-01-02T09:00:00.000Z",
                       end_time="2026-01-02T09:30:00.000Z")
    rows = list_fixed_events(conn, start_after="2026-01-01T10:00:00.000Z")
    assert [r["id"] for r in rows] == ["f2"]


def test_list_fixed_events_end_before_filter(conn):
    create_fixed_event(conn, id="f1", title="a", start_time="2026-01-01T09:00:00.000Z",
                       end_time="2026-01-01T09:30:00.000Z")
    create_fixed_event(conn, id="f2", title="b", start_time="2026-01-02T09:00:00.000Z",
                       end_time="2026-01-02T09:30:00.000Z")
    rows = list_fixed_events(conn, end_before="2026-01-01T10:00:00.000Z")
    assert [r["id"] for r in rows] == ["f1"]


def test_list_fixed_events_limit(conn):
    for i in range(5):
        create_fixed_event(
            conn, id=f"f{i}", title=f"e{i}",
            start_time=f"2026-01-0{i + 1}T09:00:00.000Z",
            end_time=f"2026-01-0{i + 1}T09:30:00.000Z",
        )
    assert len(list_fixed_events(conn, limit=2)) == 2


# ========== Update ==========


def test_update_fixed_event_changes_field(conn):
    create_fixed_event(conn, id="f1", title="a", start_time="2026-01-01T09:00:00.000Z",
                       end_time="2026-01-01T09:30:00.000Z")
    update_fixed_event(conn, "f1", title="Renamed")
    assert get_fixed_event(conn, "f1")["title"] == "Renamed"


def test_update_fixed_event_raises_on_empty_fields(conn):
    create_fixed_event(conn, id="f1", title="a", start_time="2026-01-01T09:00:00.000Z",
                       end_time="2026-01-01T09:30:00.000Z")
    with pytest.raises(ValueError):
        update_fixed_event(conn, "f1")


def test_update_fixed_event_rejects_modifying_id(conn):
    """Same rationale as the completion_log test above."""
    create_fixed_event(conn, id="f1", title="a", start_time="2026-01-01T09:00:00.000Z",
                       end_time="2026-01-01T09:30:00.000Z")
    with pytest.raises((ValueError, TypeError)):
        update_fixed_event(conn, "f1", **{"id": "f2"})


def test_update_fixed_event_returns_false_for_missing(conn):
    assert update_fixed_event(conn, "ghost", title="x") is False


# ========== Delete ==========


def test_delete_fixed_event_returns_true_when_row_existed(conn):
    create_fixed_event(conn, id="f1", title="a", start_time="2026-01-01T09:00:00.000Z",
                       end_time="2026-01-01T09:30:00.000Z")
    assert delete_fixed_event(conn, "f1") is True
    assert get_fixed_event(conn, "f1") is None


def test_delete_fixed_event_returns_false_when_missing(conn):
    assert delete_fixed_event(conn, "ghost") is False
