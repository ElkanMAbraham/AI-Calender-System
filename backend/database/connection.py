# backend/database/connection.py
# Owns the on-disk SQLite database at %APPDATA%/Docket/calendar.db.
#
# Mirrors backend/user_profile.py:
#   * Same AppData root (Docket / Docket via appdirs).
#   * Same os.makedirs(..., exist_ok=True) parent-dir pattern.
#
# Two public symbols:
#   * DB_PATH   — absolute path to calendar.db
#   * get_conn  — open a configured sqlite3.Connection
#
# Notes on PRAGMAs (SQLite's "settings" commands, applied per-connection):
#   * journal_mode = WAL     — readers don't block writers; required by the handover.
#   * synchronous  = NORMAL  — pairs with WAL; durable enough for local use, much faster than FULL.
#   * foreign_keys = ON      — SQLite ships with FKs OFF by default; the schema's
#                              ON DELETE CASCADE clauses are silently ignored without this.
#   * busy_timeout = 5000    — wait up to 5s for the lock instead of erroring immediately.
#                              Matters because pywebview may invoke api.py methods from
#                              different JS threads.

import os
import sqlite3

from appdirs import user_data_dir


# ========== App Metadata ==========
# Match backend/user_profile.py so the two files land in the same AppData root.

APP_NAME = "Docket"
APP_AUTHOR = "Docket"
DATA_DIR = user_data_dir(APP_NAME, APP_AUTHOR)

DB_PATH = os.path.join(DATA_DIR, "calendar.db")


# ========== Helpers ==========


def ensure_parent_dir(path: str) -> None:
    """Create the directory containing `path` if it doesn't exist."""
    os.makedirs(os.path.dirname(path), exist_ok=True)


# ========== Public API ==========


def get_conn(db_path: str | None = None) -> sqlite3.Connection:
    """
    Open a sqlite3.Connection with the project's standard PRAGMAs applied.

    Does NOT create the database file. Callers that need the file to exist
    (e.g. the migration runner) must ensure the parent directory exists first
    via `ensure_parent_dir`. This keeps "open a connection" a pure operation.
    """
    path = db_path if db_path is not None else DB_PATH

    conn = sqlite3.connect(
        path,
        check_same_thread=False,  # pywebview may invoke api methods from JS threads
    )
    conn.row_factory = sqlite3.Row  # convenient for CRUD callers; cheap to set

    # PRAGMAs. Each is a "setting" SQLite applies to this connection.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")

    return conn
