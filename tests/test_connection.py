# tests/test_connection.py
# Tests for backend.database.connection — get_conn() and ensure_parent_dir().
#
# These tests don't touch the schema. They verify the connection
# is opened with the right PRAGMAs and that the parent-dir helper
# does what it says.

import os

import pytest

from backend.database.connection import ensure_parent_dir, get_conn


def test_get_conn_creates_connection(tmp_path):
    """get_conn() returns a live sqlite3.Connection."""
    path = str(tmp_path / "test.db")
    conn = get_conn(path)
    try:
        assert conn is not None
        # Smoke check: a trivial query should work.
        cur = conn.execute("SELECT 1")
        assert cur.fetchone()[0] == 1
    finally:
        conn.close()


def test_get_conn_does_not_create_parent_dir(tmp_path):
    """
    Per the docstring: get_conn() is a pure "open a connection" op.
    It does NOT mkdir -p. Callers that need the dir (e.g. the migration
    runner) use ensure_parent_dir() first.
    """
    nested = tmp_path / "does" / "not" / "exist" / "yet.db"
    assert not nested.parent.exists()
    with pytest.raises(Exception):
        # sqlite3.connect() will fail because the parent dir doesn't exist
        get_conn(str(nested))


def test_ensure_parent_dir_creates_nested_path(tmp_path):
    """ensure_parent_dir should mkdir -p the parent of the given path."""
    target = tmp_path / "a" / "b" / "c" / "file.db"
    ensure_parent_dir(str(target))
    assert target.parent.exists()
    assert target.parent.is_dir()


def test_ensure_parent_dir_is_idempotent(tmp_path):
    """Calling it twice must not raise — exist_ok=True is the whole point."""
    target = tmp_path / "x" / "y.db"
    ensure_parent_dir(str(target))
    ensure_parent_dir(str(target))  # no exception
    assert target.parent.exists()


def test_get_conn_row_factory_is_sqlite_row():
    """row_factory = sqlite3.Row makes dict-style access work for callers."""
    import sqlite3
    conn = get_conn(":memory:")
    try:
        assert conn.row_factory is sqlite3.Row
    finally:
        conn.close()


def test_get_conn_applies_foreign_keys_pragma(tmp_path):
    """
    foreign_keys = ON is the most important PRAGMA. The schema declares
    ON DELETE CASCADE on schedule_blocks.task_id; without this PRAGMA
    those CASCADEs are silently ignored. Verify it's set.
    """
    path = str(tmp_path / "fk.db")
    conn = get_conn(path)
    try:
        result = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert result == 1, "foreign_keys PRAGMA must be ON"
    finally:
        conn.close()


def test_get_conn_applies_wal_journal_mode(tmp_path):
    """journal_mode = WAL — readers don't block writers, required by the
    handover. WAL may not be available for in-memory or special files;
    we use a real file to be safe."""
    path = str(tmp_path / "wal.db")
    conn = get_conn(path)
    try:
        # WAL mode persists in the file, so the value is what we set.
        result = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert result.lower() == "wal"
    finally:
        conn.close()


def test_get_conn_sets_busy_timeout(tmp_path):
    """busy_timeout = 5000ms so concurrent JS-thread calls wait briefly
    instead of erroring immediately."""
    path = str(tmp_path / "busy.db")
    conn = get_conn(path)
    try:
        result = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        assert result == 5000
    finally:
        conn.close()
