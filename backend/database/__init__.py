# backend/database/__init__.py
# Public re-exports for the database package.
#
# Lets callers keep writing:
#     from backend import database
#     database.init_db()
#     database.create_task(conn, ...)
# exactly as main.py does today. The package's implementation is split
# across connection.py, migrations.py, _helpers.py, and per-table CRUD
# modules, but the surface stays small.

from backend.database.connection import DB_PATH, get_conn
from backend.database.migrations import apply_migrations, get_schema_version


# Per-table CRUD functions. Re-exported flat so callers don't have to
# know which file each one lives in.
from backend.database.tasks import (
    create_task, get_task, list_tasks, update_task, delete_task,
)
from backend.database.fixed_events import (
    create_fixed_event, get_fixed_event, list_fixed_events,
    update_fixed_event, delete_fixed_event,
)
from backend.database.schedule_blocks import (
    create_schedule_block, get_schedule_block, list_schedule_blocks,
    update_schedule_block, delete_schedule_block,
)
from backend.database.completion_log import (
    log_completion, get_completion, list_completions,
    update_completion, delete_completion,
)
from backend.database.productivity import (
    upsert_productivity, get_productivity, list_productivity, delete_productivity,
)
from backend.database.topic_efficiency import (
    upsert_topic_efficiency, get_topic_efficiency, list_topic_efficiencies,
    delete_topic_efficiency,
)
from backend.database.event_log import (
    log_event, get_event, list_events, update_event, delete_event,
)


def init_db(db_path: str | None = None) -> None:
    """
    Apply any pending migrations to the project database.
    Called once at startup from main.py. Safe to call repeatedly.

    `db_path` defaults to the package's standard DB_PATH
    (%APPDATA%/Docket/calendar.db). Tests can pass a temp path.
    """
    apply_migrations(db_path if db_path is not None else DB_PATH)


__all__ = [
    # Connection / migration plumbing
    "DB_PATH",
    "get_conn",
    "apply_migrations",
    "get_schema_version",
    "init_db",
    # tasks
    "create_task", "get_task", "list_tasks", "update_task", "delete_task",
    # fixed_events
    "create_fixed_event", "get_fixed_event", "list_fixed_events",
    "update_fixed_event", "delete_fixed_event",
    # schedule_blocks
    "create_schedule_block", "get_schedule_block", "list_schedule_blocks",
    "update_schedule_block", "delete_schedule_block",
    # task_completion_log
    "log_completion", "get_completion", "list_completions",
    "update_completion", "delete_completion",
    # user_productivity_curve
    "upsert_productivity", "get_productivity", "list_productivity",
    "delete_productivity",
    # user_topic_efficiency
    "upsert_topic_efficiency", "get_topic_efficiency",
    "list_topic_efficiencies", "delete_topic_efficiency",
    # task_event_log
    "log_event", "get_event", "list_events", "update_event", "delete_event",
]
