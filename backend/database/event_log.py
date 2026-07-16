# backend/database/event_log.py
# CRUD for `task_event_log` — full audit trail for every scheduling
# event and status change. Like task_completion_log, this is
# write-mostly in practice (you don't edit history).
#
# Rows are referenced by the scheduling layer for "what changed and
# why" explanations, and by the AI context builder for recent
# activity.

import sqlite3

from backend.database._helpers import coerce_filter_value, row_to_dict


# ========== Columns ==========

_COLUMNS = (
    "id",
    "task_id",
    "event_type",
    "old_value",
    "new_value",
    "reason",
    "created_at",
)


# ========== Create / Read ==========


def log_event(
    conn: sqlite3.Connection,
    *,
    id: str,
    task_id: str,
    event_type: str,
    old_value: str | None = None,
    new_value: str | None = None,
    reason: str | None = None,
) -> None:
    """
    Append an event. `event_type` must be one of the schema's CHECK
    values: 'scheduled', 'rescheduled', 'status_change', 'completed',
    'cancelled', 'manually_moved'.
    """
    conn.execute(
        """
        INSERT INTO task_event_log (
            id, task_id, event_type, old_value, new_value, reason
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            id,
            task_id,
            event_type,
            coerce_filter_value(old_value),
            coerce_filter_value(new_value),
            coerce_filter_value(reason),
        ),
    )
    conn.commit()


def get_event(conn: sqlite3.Connection, id: str) -> dict | None:
    row = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM task_event_log WHERE id = ?",
        (id,),
    ).fetchone()
    return row_to_dict(row)


def list_events(
    conn: sqlite3.Connection,
    *,
    task_id: str | None = None,
    event_type: str | None = None,
    since: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """
    List events. The natural default ordering is newest-first
    (created_at DESC) so recent activity is at the top.
    """
    clauses: list[str] = []
    params: list[object] = []

    if task_id is not None:
        clauses.append("task_id = ?")
        params.append(task_id)
    if event_type is not None:
        clauses.append("event_type = ?")
        params.append(event_type)
    if since is not None:
        clauses.append("created_at >= ?")
        params.append(since)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit_clause = f"LIMIT {int(limit)}" if limit is not None else ""

    rows = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM task_event_log {where} "
        f"ORDER BY created_at DESC {limit_clause}",
        params,
    ).fetchall()
    return [row_to_dict(r) for r in rows]


# ========== Update / Delete ==========


def update_event(conn: sqlite3.Connection, id: str, **fields) -> bool:
    """
    Partial update. Like completion_log, this is mostly write-once;
    shipped for symmetry and corrections.
    """
    if not fields:
        raise ValueError("update_event requires at least one field")

    set_clauses = []
    params: list[object] = []
    for col, value in fields.items():
        if col == "id":
            raise ValueError("id cannot be modified via update_event")
        set_clauses.append(f"{col} = ?")
        params.append(coerce_filter_value(value))
    params.append(id)

    cursor = conn.execute(
        f"UPDATE task_event_log SET {', '.join(set_clauses)} WHERE id = ?",
        params,
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_event(conn: sqlite3.Connection, id: str) -> bool:
    cursor = conn.execute("DELETE FROM task_event_log WHERE id = ?", (id,))
    conn.commit()
    return cursor.rowcount > 0
