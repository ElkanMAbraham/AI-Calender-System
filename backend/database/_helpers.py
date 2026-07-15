# backend/database/_helpers.py
# Internal utilities shared by the per-table CRUD modules.
# Not exported from the package — CRUD modules import these directly.
#
# Why this exists:
#   * `now_iso()` — produce the schema's standard timestamp string
#     ("...Z" suffix, millisecond precision) without every CRUD function
#     re-deriving the format.
#   * `build_update_sql()` — render an UPDATE statement that bumps
#     `updated_at` to now while letting the caller set any other columns.
#     The `strftime(...)` expression has to be inlined as raw SQL because
#     SQLite parameters can only carry values, not SQL fragments.
#   * `row_to_dict()` — convert a sqlite3.Row to a plain dict so callers
#     can json.dumps() it without surprises.
#   * `coerce_filters()` — translate a few common "missing" sentinels
#     (None, "") into SQL-friendly representations.

import sqlite3
from datetime import datetime, timezone


# ========== Timestamps ==========


def now_iso() -> str:
    """
    Current UTC time as "YYYY-MM-DDTHH:MM:SS.sssZ".

    Matches the schema's strftime('%Y-%m-%dT%H:%M:%fZ', 'now') format
    (truncated to milliseconds) so timestamps sort as strings and
    round-trip cleanly with the rest of the app.
    """
    # datetime(...).isoformat() gives "YYYY-MM-DDTHH:MM:SS.ffffff+00:00"
    # We need millisecond precision and a trailing "Z".
    return (
        datetime.now(timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%f")[:-3]
        + "Z"
    )


# ========== SQL builders ==========


def build_update_sql(table: str, fields: dict[str, object]) -> tuple[str, list[object]]:
    """
    Build an UPDATE statement that sets each key in `fields` and also
    bumps `updated_at` to the current time.

    Returns (sql, params). `updated_at` is rendered as a raw SQL
    expression (strftime) because SQLite parameters can't carry SQL
    fragments; other values are still parameterized safely.

    Usage:
        sql, params = build_update_sql("tasks", {"title": "New"})
        conn.execute(sql, params)  # → UPDATE tasks SET title=?, updated_at=strftime(...) WHERE id=?
    """
    if not fields:
        raise ValueError("build_update_sql requires at least one field")

    # We split out `id` so the WHERE clause uses it; everything else
    # becomes a SET clause.
    where_id = fields.get("id")
    if where_id is None:
        raise ValueError("build_update_sql requires an 'id' field for the WHERE clause")

    set_columns = [k for k in fields if k != "id"]
    set_columns.append("updated_at")

    # The strftime expression is inlined as raw SQL; other values become "?" params.
    set_clauses = []
    params: list[object] = []
    for col in set_columns:
        if col == "updated_at":
            set_clauses.append("updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')")
        else:
            set_clauses.append(f"{col} = ?")
            params.append(fields[col])

    params.append(where_id)
    sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE id = ?"
    return sql, params


# ========== Row conversion ==========


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    """Convert a sqlite3.Row to a plain dict, or pass through None."""
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


# ========== Filter coercion ==========


def coerce_filter_value(value: object) -> object:
    """
    Translate Python "missing" sentinels into SQL-friendly forms.

    Rules:
      * None        → None        (passes through, IS NULL checks are
                                   the caller's job)
      * "" (empty)  → None        (an empty string for an ISO timestamp
                                   or topic isn't meaningful; treat as
                                   "not set")
    """
    if value == "":
        return None
    return value
