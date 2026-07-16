# backend/database/__init__.py
# Public re-exports for the database package.
#
# Lets callers keep writing:
#     from backend import database
#     database.init_db()
# exactly as main.py does today. The package's implementation is split
# across connection.py, migrations.py, and (later) per-table modules,
# but the surface stays small.

from backend.database.connection import DB_PATH, get_conn
from backend.database.migrations import apply_migrations, get_schema_version


def init_db() -> None:
    """
    Apply any pending migrations to the project database.
    Called once at startup from main.py. Safe to call repeatedly.
    """
    apply_migrations(DB_PATH)


__all__ = [
    "DB_PATH",
    "get_conn",
    "apply_migrations",
    "get_schema_version",
    "init_db",
]
