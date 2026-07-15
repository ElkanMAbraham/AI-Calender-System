# backend/database/productivity.py
# CRUD for `user_productivity_curve` — aggregate efficiency per
# (day_of_week, hour_of_day). Primary key is the composite of those
# two integers, so `get`/`update` take both as args.
#
# Per project-db-decisions, this table is incrementally updated when
# task_completion_log changes. That updater lives in a future plan.
# This module just exposes the data.

import sqlite3

from backend.database._helpers import row_to_dict


# ========== Columns ==========

_COLUMNS = (
    "day_of_week",
    "hour_of_day",
    "efficiency_score",
)


# ========== Create / Read ==========


def upsert_productivity(
    conn: sqlite3.Connection,
    *,
    day_of_week: int,
    hour_of_day: int,
    efficiency_score: float,
) -> None:
    """
    Insert or update the productivity score for one (day, hour) cell.
    This is the only "write" operation that makes sense for this
    table — there's no create-vs-update distinction at the row level.
    """
    conn.execute(
        """
        INSERT INTO user_productivity_curve (day_of_week, hour_of_day, efficiency_score)
        VALUES (?, ?, ?)
        ON CONFLICT(day_of_week, hour_of_day) DO UPDATE SET
            efficiency_score = excluded.efficiency_score
        """,
        (day_of_week, hour_of_day, efficiency_score),
    )
    conn.commit()


def get_productivity(
    conn: sqlite3.Connection,
    *,
    day_of_week: int,
    hour_of_day: int,
) -> dict | None:
    row = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM user_productivity_curve "
        "WHERE day_of_week = ? AND hour_of_day = ?",
        (day_of_week, hour_of_day),
    ).fetchone()
    return row_to_dict(row)


def list_productivity(conn: sqlite3.Connection) -> list[dict]:
    """
    Return all 168 (or fewer) cells, ordered for the heatmap view:
    day_of_week ASC, hour_of_day ASC.
    """
    rows = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM user_productivity_curve "
        "ORDER BY day_of_week ASC, hour_of_day ASC"
    ).fetchall()
    return [row_to_dict(r) for r in rows]


# ========== Update / Delete ==========


def delete_productivity(
    conn: sqlite3.Connection,
    *,
    day_of_week: int,
    hour_of_day: int,
) -> bool:
    cursor = conn.execute(
        "DELETE FROM user_productivity_curve "
        "WHERE day_of_week = ? AND hour_of_day = ?",
        (day_of_week, hour_of_day),
    )
    conn.commit()
    return cursor.rowcount > 0
