# backend/database/topic_efficiency.py
# CRUD for `user_topic_efficiency` — per-topic speed multiplier
# (0.8 = 20% faster than the task's own estimate).
#
# Primary key is `topic` (a string). The table has a `last_updated`
# column that SQLite's strftime default populates; updates can leave
# it alone (the existing value stays) or a future plan could touch
# it explicitly.
#
# Per project-db-decisions, this is incrementally updated when
# task_completion_log changes. The updater lives in a future plan.

import sqlite3

from backend.database._helpers import row_to_dict


# ========== Columns ==========

_COLUMNS = (
    "topic",
    "efficiency_multiplier",
    "last_updated",
)


# ========== Create / Read ==========


def upsert_topic_efficiency(
    conn: sqlite3.Connection,
    *,
    topic: str,
    efficiency_multiplier: float,
) -> None:
    """
    Insert or update the efficiency multiplier for a topic.
    Like productivity.py, no separate create/update — the operation
    is intrinsically "set this cell."
    """
    conn.execute(
        """
        INSERT INTO user_topic_efficiency (topic, efficiency_multiplier)
        VALUES (?, ?)
        ON CONFLICT(topic) DO UPDATE SET
            efficiency_multiplier = excluded.efficiency_multiplier,
            last_updated = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        """,
        (topic, efficiency_multiplier),
    )
    conn.commit()


def get_topic_efficiency(conn: sqlite3.Connection, topic: str) -> dict | None:
    row = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM user_topic_efficiency WHERE topic = ?",
        (topic,),
    ).fetchone()
    return row_to_dict(row)


def list_topic_efficiencies(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM user_topic_efficiency "
        "ORDER BY topic ASC"
    ).fetchall()
    return [row_to_dict(r) for r in rows]


# ========== Update / Delete ==========


def delete_topic_efficiency(conn: sqlite3.Connection, topic: str) -> bool:
    cursor = conn.execute(
        "DELETE FROM user_topic_efficiency WHERE topic = ?",
        (topic,),
    )
    conn.commit()
    return cursor.rowcount > 0
