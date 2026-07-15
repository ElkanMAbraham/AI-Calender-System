# backend/database/fixed_events.py
# CRUD for `fixed_events` — immutable calendar entries the AI must
# schedule around (meetings, appointments, etc.).
#
# No `updated_at`: fixed_events are immutable in spirit. The schema
# doesn't track creation time either, so the table is fully
# write-once / read-many in practice.

import sqlite3

from backend.database._helpers import coerce_filter_value, row_to_dict


# ========== Columns ==========

_COLUMNS = (
    "id",
    "title",
    "start_time",
    "end_time",
    "recurrence_rule",
    "source",
)


# ========== Create / Read ==========


def create_fixed_event(
    conn: sqlite3.Connection,
    *,
    id: str,
    title: str,
    start_time: str,
    end_time: str,
    recurrence_rule: str | None = None,
    source: str | None = None,
) -> None:
    """
    Insert a fixed event. start_time and end_time are ISO 8601 UTC.
    The CRUD layer does NOT validate start < end — that's the
    scheduling layer's job.
    """
    conn.execute(
        """
        INSERT INTO fixed_events (id, title, start_time, end_time, recurrence_rule, source)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            id,
            title,
            start_time,
            end_time,
            coerce_filter_value(recurrence_rule),
            coerce_filter_value(source),
        ),
    )
    conn.commit()


def get_fixed_event(conn: sqlite3.Connection, id: str) -> dict | None:
    row = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM fixed_events WHERE id = ?",
        (id,),
    ).fetchone()
    return row_to_dict(row)


def list_fixed_events(
    conn: sqlite3.Connection,
    *,
    start_after: str | None = None,
    end_before: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """
    List fixed events, optionally filtered by time range. Useful for
    the AI scheduling layer: "give me everything in the next 7 days."
    """
    clauses: list[str] = []
    params: list[object] = []

    if start_after is not None:
        clauses.append("end_time > ?")
        params.append(start_after)
    if end_before is not None:
        clauses.append("start_time < ?")
        params.append(end_before)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit_clause = f"LIMIT {int(limit)}" if limit is not None else ""

    rows = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM fixed_events {where} "
        f"ORDER BY start_time ASC {limit_clause}",
        params,
    ).fetchall()
    return [row_to_dict(r) for r in rows]


# ========== Update / Delete ==========


def update_fixed_event(conn: sqlite3.Connection, id: str, **fields) -> bool:
    """
    Partial update. fixed_events have no `updated_at` column, so we
    build the UPDATE without touching that.

    Note: in practice fixed_events are immutable. This exists for
    completeness and rare correction flows.
    """
    if not fields:
        raise ValueError("update_fixed_event requires at least one field")

    set_clauses = []
    params: list[object] = []
    for col, value in fields.items():
        if col == "id":
            raise ValueError("id cannot be modified via update_fixed_event")
        set_clauses.append(f"{col} = ?")
        params.append(coerce_filter_value(value))
    params.append(id)

    cursor = conn.execute(
        f"UPDATE fixed_events SET {', '.join(set_clauses)} WHERE id = ?",
        params,
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_fixed_event(conn: sqlite3.Connection, id: str) -> bool:
    cursor = conn.execute("DELETE FROM fixed_events WHERE id = ?", (id,))
    conn.commit()
    return cursor.rowcount > 0
