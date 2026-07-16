# tests/test_migrations.py
# Tests for backend.database.migrations — apply_migrations and get_schema_version.
#
# Key behaviors we lock in:
#   1. apply_migrations creates the file if missing.
#   2. apply_migrations is idempotent — running twice doesn't re-apply.
#   3. apply_migrations records each version in schema_version.
#   4. get_schema_version returns 0 for a non-existent DB.
#   5. The schema_version table itself is created on first run.
#   6. Migrations actually create the expected tables (sanity check).

import os

from backend.database import apply_migrations, get_schema_version
from backend.database.connection import get_conn


def test_apply_migrations_creates_file(tmp_path):
    """The DB file should exist after a fresh apply_migrations call."""
    path = str(tmp_path / "fresh.db")
    assert not os.path.exists(path)
    apply_migrations(path)
    assert os.path.exists(path)


def test_apply_migrations_is_idempotent(tmp_path):
    """Running apply_migrations twice must not re-apply or error."""
    path = str(tmp_path / "idempotent.db")
    apply_migrations(path)
    v1 = get_schema_version(path)

    apply_migrations(path)  # second call
    v2 = get_schema_version(path)

    assert v1 == v2, "second apply_migrations should not bump the version"


def test_apply_migrations_records_version(tmp_path):
    """schema_version table should reflect the highest-numbered SQL file."""
    path = str(tmp_path / "versioned.db")
    apply_migrations(path)
    v = get_schema_version(path)
    # There's currently one migration in schema/ (001_initial.sql).
    assert v >= 1


def test_get_schema_version_returns_zero_for_missing_db(tmp_path):
    """A non-existent file should read as version 0 (no migrations run)."""
    path = str(tmp_path / "ghost.db")
    assert not os.path.exists(path)
    assert get_schema_version(path) == 0


def test_get_schema_version_works_on_real_db(db_path):
    """The conftest's `db_path` fixture has migrations applied; the version
    should be at least 1."""
    assert get_schema_version(db_path) >= 1


def test_apply_migrations_creates_schema_version_table(tmp_path):
    """The bookkeeping table itself must be created on first run."""
    path = str(tmp_path / "bookkeeping.db")
    apply_migrations(path)
    conn = get_conn(path)
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ).fetchone()
        assert row is not None
    finally:
        conn.close()


def test_apply_migrations_creates_all_seven_tables(db_path):
    """
    Sanity check: the initial migration (001_initial.sql) declares all
    7 tables. Lock that in so a future migration that drops one of them
    trips a loud test failure.
    """
    expected = {
        "tasks",
        "fixed_events",
        "schedule_blocks",
        "task_completion_log",
        "user_productivity_curve",
        "user_topic_efficiency",
        "task_event_log",
        "schema_version",  # bookkeeping
    }
    conn = get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        actual = {r["name"] for r in rows}
        assert expected.issubset(actual), f"missing tables: {expected - actual}"
    finally:
        conn.close()


def test_apply_migrations_creates_indexes(db_path):
    """The initial migration also creates 8 indexes. Spot-check a few."""
    expected_indexes = {
        "idx_tasks_status",
        "idx_schedule_blocks_task",
        "idx_completion_log_completed_at",
    }
    conn = get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        actual = {r["name"] for r in rows}
        # System indexes (sqlite_autoindex_*) also exist; we only check ours.
        for idx in expected_indexes:
            assert idx in actual, f"missing index: {idx}"
    finally:
        conn.close()
