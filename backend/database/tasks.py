# backend/database/tasks.py
# CRUD for the `tasks` table — the core "intent" entity.
#
# The "intent" half of the app: a task says WHAT needs to be done and
# roughly HOW LONG, with no scheduling info. The AI consumes tasks
# (plus fixed_events) and produces schedule_blocks.
#
# All functions take an open sqlite3.Connection — the caller is
# responsible for opening/closing it. CRUD never opens connections.

import sqlite3

from backend.database._helpers import build_update_sql, coerce_filter_value, row_to_dict


# ========== Columns ==========
# Centralized so the create/list SQL stays in sync with the schema.

_COLUMNS = (
    "id",
    "title",
    "estimated_duration_minutes",
    "deadline",
    "earliest_start",
    "priority",
    "topic",
    "status",
    "recurrence_rule",
    "created_at",
    "updated_at",
)


# ========== Create / Read ==========


def create_task(
    conn: sqlite3.Connection,
    *,
    id: str,
    title: str,
    estimated_duration_minutes: int,
    deadline: str | None = None,
    earliest_start: str | None = None,
    priority: int = 3,
    topic: str | None = None,
    status: str = "pending",
    recurrence_rule: str | None = None,
) -> None:
    """
    Insert a new task. `id` and `title` are required; everything else
    has a schema default. `created_at` and `updated_at` are set by
    SQLite's strftime default.
    """
    conn.execute(
        """
        INSERT INTO tasks (
            id, title, estimated_duration_minutes, deadline, earliest_start,
            priority, topic, status, recurrence_rule
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            id,
            title,
            estimated_duration_minutes,
            coerce_filter_value(deadline),
            coerce_filter_value(earliest_start),
            priority,
            coerce_filter_value(topic),
            status,
            coerce_filter_value(recurrence_rule),
        ),
    )
    conn.commit()


def get_task(conn: sqlite3.Connection, id: str) -> dict | None:
    """Return a single task as a dict, or None if not found."""
    row = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM tasks WHERE id = ?",
        (id,),
    ).fetchone()
    return row_to_dict(row)


def list_tasks(
    conn: sqlite3.Connection,
    *,
    status: str | None = None,
    topic: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """
    List tasks, optionally filtered by status and/or topic.
    Returns a list of dicts (empty list if none match).
    """
    clauses: list[str] = []
    params: list[object] = []

    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    if topic is not None:
        clauses.append("topic = ?")
        params.append(topic)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit_clause = f"LIMIT {int(limit)}" if limit is not None else ""

    rows = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM tasks {where} "
        f"ORDER BY created_at DESC {limit_clause}",
        params,
    ).fetchall()
    return [row_to_dict(r) for r in rows]


# ========== Update / Delete ==========


def update_task(conn: sqlite3.Connection, id: str, **fields) -> bool:
    """
    Partial update. `updated_at` is bumped automatically. Returns True
    if a row was changed, False if the id didn't exist.

    `**fields` accepts any subset of the task columns EXCEPT `id` and
    `created_at` (use the table's defaults for those).
    """
    if "created_at" in fields:
        raise ValueError("created_at cannot be modified via update_task")

    fields = {**fields, "id": id}  # build_update_sql needs id in the dict
    sql, params = build_update_sql("tasks", fields)
    cursor = conn.execute(sql, params)
    conn.commit()
    return cursor.rowcount > 0


def delete_task(conn: sqlite3.Connection, id: str) -> bool:
    """
    Delete a task. ON DELETE CASCADE on schedule_blocks will follow.

    History rows (task_event_log, task_completion_log) are NOT cascaded
    by design — the schema REFERENCES tasks(id) without ON DELETE
    CASCADE, so this function will raise sqlite3.IntegrityError if the
    task still has history. Callers that want a hard delete must
    remove the history rows first; callers that want "soft delete"
    should set status='cancelled' via update_task instead.

    Returns True if a row was deleted, False if the id didn't exist.
    """
    cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (id,))
    conn.commit()
    return cursor.rowcount > 0
