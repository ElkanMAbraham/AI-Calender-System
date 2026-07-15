# tests/conftest.py
# Shared pytest fixtures.
#
# pytest auto-discovers fixtures defined here — any test_*.py file under
# tests/ can request these by name without importing them. Keeping the
# setup in one place means a test file can be just: "given a clean DB,
# then assert X."
#
# Three layers of fixtures:
#   1. db_path  — a fresh, migrated SQLite file under tmp_path
#   2. conn     — an open sqlite3.Connection to that file
#   3. settings_dir — user_profile's AppData dir, redirected to tmp_path
#                     (so tests NEVER touch the user's real settings.json)
#   4. api      — an Api() instance wired up to use both the tmp DB and
#                 the tmp settings dir (for full integration tests)
#
# Every test that asks for `conn` or `db_path` gets a brand-new database.
# That isolation is why we use tmp_path (pytest's auto-cleaned scratch dir)
# and apply_migrations() in the fixture body — no shared state leaks
# between tests.

import pytest

from backend import database, user_profile
from backend.api import Api
from backend.database import apply_migrations, get_conn


# ========== DB fixtures ==========


@pytest.fixture
def db_path(tmp_path):
    """
    A path to a fresh calendar.db under tmp_path, with all migrations
    already applied. Tests request this when they want to open their own
    connection (rare; most just ask for `conn`).
    """
    path = tmp_path / "calendar.db"
    apply_migrations(str(path))
    return str(path)


@pytest.fixture
def conn(db_path):
    """
    An open sqlite3.Connection to the test DB.

    The same PRAGMAs (WAL, foreign_keys=ON, etc.) as production apply,
    so cascade and busy-timeout behavior is the same in tests as in the
    real app.
    """
    c = get_conn(db_path)
    try:
        yield c
    finally:
        c.close()


# ========== Settings fixtures ==========


@pytest.fixture
def settings_dir(monkeypatch, tmp_path):
    """
    Redirect user_profile's AppData dir to a temp directory for the
    duration of one test.

    The previous smoke test got blocked for writing to the user's real
    %APPDATA%/Docket/settings.json. This fixture makes that impossible:
    every test that touches settings runs against a tmp dir, and
    monkeypatch restores the real path the moment the test ends.
    """
    d = tmp_path / "userdata"
    d.mkdir()
    monkeypatch.setattr(user_profile, "SETTINGS_DIR", str(d))
    return d


# ========== API integration fixture ==========


@pytest.fixture
def api(monkeypatch, db_path, settings_dir):
    """
    A fresh Api() instance wired to the tmp DB and the tmp settings dir.

    We monkeypatch BOTH `database.DB_PATH` and `database.connection.DB_PATH`.
    They're the same string at import time, but the connection module
    re-imports it as a module-local name, and `get_conn()` reads the
    module-local. Patching only `database.DB_PATH` would silently
    leave get_conn() pointing at the real %APPDATA% DB.

    `settings_dir` is part of the fixture graph for its side effect —
    the monkeypatch it sets is what keeps Api.savePreferences() safe.
    """
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(database.connection, "DB_PATH", db_path)
    return Api()
