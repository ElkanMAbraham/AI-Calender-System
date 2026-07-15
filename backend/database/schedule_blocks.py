# backend/database/schedule_blocks.py
# CRUD for `schedule_blocks` — the AI's current plan. Each row is a
# concrete time-blocked piece of work tied to a task.
#
# Important: this table has no `updated_at`. Reasoning: blocks are
# versioned via the `version` column (1, 2, 3, ...) and replaced in
# bulk when the AI re-plans. We expose a `bump_version` helper for
# that.
#
# ON DELETE CASCADE from tasks means deleting a task also deletes
# its blocks.

import sqlite3

from backend.database._helpers import coerce_filter_value, row_to_dict


# ========== Columns ==========

_COLUMNS = (
    "id",
    "task_id",
    "start_time",
    "end_time",
    "status",
    "reasoning",
    "is_pinned",
    "created_at",
    "version",
)


# ========== Create / Read ==========


def create_schedule_block(
    conn: sqlite3.Connection,
    *,
    id: str,
    task_id: str,
    start_time: str,
    end_time: str,
    status: str = "planned",
    reasoning: str | None = None,
    is_pinned: bool = False,
    version: int = 1,
) -> None:
    """
    Insert a schedule block. `is_pinned` is stored as INTEGER 0/1
    per the schema's CHECK constraint.
    """
    conn.execute(
        """
        INSERT INTO schedule_blocks (
            id, task_id, start_time, end_time, status, reasoning, is_pinned, version
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            id,
            task_id,
            start_time,
            end_time,
            status,
            coerce_filter_value(reasoning),
            1 if is_pinned else 0,
            version,
        ),
    )
    conn.commit()


def get_schedule_block(conn: sqlite3.Connection, id: str) -> dict | None:
    row = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM schedule_blocks WHERE id = ?",
        (id,),
    ).fetchone()
    return row_to_dict(row)


def list_schedule_blocks(
    conn: sqlite3.Connection,
    *,
    task_id: str | None = None,
    status: str | None = None,
    start_after: str | None = None,
    end_before: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """
    List schedule blocks. The most common query is "all planned
    blocks in a time range" — combine `status='planned'` with
    `start_after` / `end_before`.
    """
    clauses: list[str] = []
    params: list[object] = []

    if task_id is not None:
        clauses.append("task_id = ?")
        params.append(task_id)
    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    if start_after is not None:
        clauses.append("end_time > ?")
        params.append(start_after)
    if end_before is not None:
        clauses.append("start_time < ?")
        params.append(end_before)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit_clause = f"LIMIT {int(limit)}" if limit is not None else ""

    rows = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM schedule_blocks {where} "
        f"ORDER BY start_time ASC {limit_clause}",
        params,
    ).fetchall()
    return [row_to_dict(r) for r in rows]


# ========== Update / Delete ==========


def update_schedule_block(conn: sqlite3.Connection, id: str, **fields) -> bool:
    """
    Partial update. Like fixed_events, this table has no
    `updated_at` — blocks are versioned, not timestamped.
    """
    if not fields:
        raise ValueError("update_schedule_block requires at least one field")

    if "is_pinned" in fields:
        fields["is_pinned"] = 1 if fields["is_pinned"] else 0

    set_clauses = []
    params: list[object] = []
    for col, value in fields.items():
        if col == "id":
            raise ValueError("id cannot be modified via update_schedule_block")
        set_clauses.append(f"{col} = ?")
        params.append(coerce_filter_value(value))
    params.append(id)

    cursor = conn.execute(
        f"UPDATE schedule_blocks SET {', '.join(set_clauses)} WHERE id = ?",
        params,
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_schedule_block(conn: sqlite3.Connection, id: str) -> bool:
    cursor = conn.execute("DELETE FROM schedule_blocks WHERE id = ?", (id,))
    conn.commit()
    return cursor.rowcount > 0
