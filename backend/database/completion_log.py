# backend/database/completion_log.py
# CRUD for `task_completion_log` — the AI's behavioural record.
#
# In practice, rows here are written once (when a task is finished)
# and rarely read directly. The derived tables (user_productivity_curve,
# user_topic_efficiency) are computed FROM this table.
#
# Per project-db-decisions, the derived-table updaters are deferred
# to a separate plan. This module just persists rows.

import sqlite3

from backend.database._helpers import coerce_filter_value, row_to_dict


# ========== Columns ==========

_COLUMNS = (
    "id",
    "task_id",
    "completed_at",
    "actual_duration_minutes",
    "planned_duration_minutes",
    "topic",
    "start_time",
    "confidence",
)


# ========== Create / Read ==========


def log_completion(
    conn: sqlite3.Connection,
    *,
    id: str,
    task_id: str,
    completed_at: str,
    actual_duration_minutes: int,
    planned_duration_minutes: int,
    topic: str,
    start_time: str,
    confidence: float = 1.0,
) -> None:
    """
    Append a completion event. Note: the foreign key to `tasks` is
    plain REFERENCES (no CASCADE) — a completion log row survives
    task deletion by design (history is precious).
    """
    conn.execute(
        """
        INSERT INTO task_completion_log (
            id, task_id, completed_at, actual_duration_minutes,
            planned_duration_minutes, topic, start_time, confidence
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            id,
            task_id,
            completed_at,
            actual_duration_minutes,
            planned_duration_minutes,
            coerce_filter_value(topic),
            start_time,
            confidence,
        ),
    )
    conn.commit()


def get_completion(conn: sqlite3.Connection, id: str) -> dict | None:
    row = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM task_completion_log WHERE id = ?",
        (id,),
    ).fetchone()
    return row_to_dict(row)


def list_completions(
    conn: sqlite3.Connection,
    *,
    task_id: str | None = None,
    topic: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """
    List completion-log rows. The AI scheduling layer queries this
    for context (recent completions, per-topic averages).
    """
    clauses: list[str] = []
    params: list[object] = []

    if task_id is not None:
        clauses.append("task_id = ?")
        params.append(task_id)
    if topic is not None:
        clauses.append("topic = ?")
        params.append(topic)
    if since is not None:
        clauses.append("completed_at >= ?")
        params.append(since)
    if until is not None:
        clauses.append("completed_at < ?")
        params.append(until)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit_clause = f"LIMIT {int(limit)}" if limit is not None else ""

    rows = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM task_completion_log {where} "
        f"ORDER BY completed_at DESC {limit_clause}",
        params,
    ).fetchall()
    return [row_to_dict(r) for r in rows]


# ========== Update / Delete ==========


def update_completion(conn: sqlite3.Connection, id: str, **fields) -> bool:
    """
    Partial update. History is usually write-once, but we ship
    update/delete for symmetry and for backfilling corrections
    (e.g. fixing a typo'd topic).
    """
    if not fields:
        raise ValueError("update_completion requires at least one field")

    set_clauses = []
    params: list[object] = []
    for col, value in fields.items():
        if col == "id":
            raise ValueError("id cannot be modified via update_completion")
        set_clauses.append(f"{col} = ?")
        params.append(coerce_filter_value(value))
    params.append(id)

    cursor = conn.execute(
        f"UPDATE task_completion_log SET {', '.join(set_clauses)} WHERE id = ?",
        params,
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_completion(conn: sqlite3.Connection, id: str) -> bool:
    cursor = conn.execute("DELETE FROM task_completion_log WHERE id = ?", (id,))
    conn.commit()
    return cursor.rowcount > 0
