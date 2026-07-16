# backend/database/migrations.py
# Hand-rolled migration runner. ~50 lines, no external dependencies.
#
# Mental model: "a list of SQL scripts that need to be run, in order,
# exactly once per device." The runner figures out which scripts are
# pending and applies them.
#
# Filename convention for files in backend/database/schema/:
#   NNN_descriptive_name.sql     (e.g. 001_initial.sql, 002_add_task_color.sql)
#   NNN is an integer version. Files are applied in sorted order.
#
# Bookkeeping lives in a tiny `schema_version` table in the DB itself:
#   version INTEGER PRIMARY KEY   -- one row per applied migration
#   applied_at TEXT NOT NULL
#
# What this runner does NOT do:
#   * No data migrations in this plan. Initial migration is pure DDL.
#   * No rollback. Add a new migration that undoes a change instead.
#   * No PRAGMAs inside SQL files — PRAGMAs are per-connection in
#     backend.database.connection.

import os
import re
import sqlite3

from backend.database.connection import DB_PATH, ensure_parent_dir, get_conn


# Capture the leading integer prefix of a migration filename.
_VERSION_PREFIX = re.compile(r"^(\d+)_")


# ========== Public API ==========


def apply_migrations(db_path: str = DB_PATH) -> None:
    """
    Ensure `db_path` exists and all pending SQL migrations in
    backend/database/schema/ have been applied, in order.

    Safe to call repeatedly: the second call is a no-op once the
    schema is current.
    """
    ensure_parent_dir(db_path)

    # Open a connection to create the file if it doesn't exist yet.
    # We use the same get_conn() callers will use, so PRAGMAs (WAL etc.)
    # are applied on the very first connection too.
    conn = get_conn(db_path)
    try:
        _ensure_version_table(conn)
        current = _current_version(conn)

        schema_dir = _schema_dir()
        for version, sql_path in _pending_migrations(schema_dir, current):
            _apply_one(conn, version, sql_path)
    finally:
        conn.close()


def get_schema_version(db_path: str = DB_PATH) -> int:
    """
    Return the highest applied migration version, or 0 if none have run.
    Useful for debugging and for future startup banners.
    """
    if not os.path.exists(db_path):
        return 0

    conn = get_conn(db_path)
    try:
        return _current_version(conn)
    finally:
        conn.close()


# ========== Internals ==========


def _ensure_version_table(conn: sqlite3.Connection) -> None:
    """Create the bookkeeping table if it doesn't exist yet."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version    INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
                        DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )
    conn.commit()


def _current_version(conn: sqlite3.Connection) -> int:
    """Highest applied version, or 0 if no migrations have run yet."""
    row = conn.execute(
        "SELECT COALESCE(MAX(version), 0) AS v FROM schema_version"
    ).fetchone()
    return int(row["v"])


def _schema_dir() -> str:
    """Absolute path to the schema/ directory next to this file."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "schema")


def _pending_migrations(schema_dir: str, current: int):
    """
    Yield (version, absolute_path) for every *.sql file in schema_dir
    whose numeric prefix is strictly greater than `current`, in ascending
    order. Skips files that don't start with an integer prefix.
    """
    if not os.path.isdir(schema_dir):
        return

    candidates = []
    for name in os.listdir(schema_dir):
        if not name.endswith(".sql"):
            continue
        match = _VERSION_PREFIX.match(name)
        if not match:
            continue
        version = int(match.group(1))
        if version > current:
            candidates.append((version, os.path.join(schema_dir, name)))

    candidates.sort(key=lambda pair: pair[0])
    yield from candidates


def _apply_one(conn: sqlite3.Connection, version: int, sql_path: str) -> None:
    """
    Apply a single migration in a transaction, then record its version.
    Raises on any error so a broken migration stops startup loudly.
    """
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    try:
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_version (version) VALUES (?)",
            (version,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
