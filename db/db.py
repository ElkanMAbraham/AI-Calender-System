import sqlite3
import json
from datetime import datetime

DB_PATH = "calendar.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # -----------------------------------------------------------------
    # USER PROFILE
    # Stores onboarding answers and AI provider config.
    # The ai_context column is a JSON blob the AI can read to understand
    # the user's habits before making any estimates.
    # -----------------------------------------------------------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id              INTEGER PRIMARY KEY CHECK (id = 1),  -- only one row ever
            name            TEXT,
            primary_use     TEXT,   -- 'work', 'study', 'personal', 'mix'
            ai_provider     TEXT DEFAULT 'claude',  -- 'claude', 'ollama', 'openai'
            ai_api_key      TEXT,   -- stored locally, never transmitted
            autonomy_level  TEXT DEFAULT 'notify',  -- 'ask', 'notify', 'autonomous'        --check 'AI summer project DOC for for information'
            -- JSON blob: {"frequent_tasks": [{"name": "essay", "avg_hours": 3}]}
            -- AI reads this at startup to seed its estimates
            ai_context      TEXT DEFAULT '{}', -- information from onboarding
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # -----------------------------------------------------------------
    # TASKS
    # Core table. AI-relevant columns are:
    #   - ai_estimated_hours: what the AI predicted
    #   - actual_hours: what actually happened (AI learns from the gap)
    #   - ai_reasoning: the AI's explanation for its estimate, shown to user
    #   - ai_tags: JSON array of tags AI assigned e.g. ["essay", "research"]
    #   - context_snapshot: JSON of what the AI knew when it made estimates
    # -----------------------------------------------------------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            title               TEXT NOT NULL,
            description         TEXT,
            difficulty          INTEGER CHECK (difficulty BETWEEN 1 AND 5),
            deadline            TEXT,   -- ISO datetime string
            status              TEXT DEFAULT 'pending',  -- 'pending', 'in_progress', 'done', 'overdue'
            is_repeating        INTEGER DEFAULT 0,
            repeat_interval     TEXT,   -- 'daily', 'weekly', 'monthly'
            completion_pct      INTEGER DEFAULT 0 CHECK (completion_pct BETWEEN 0 AND 100),

            -- AI estimation columns
            ai_estimated_hours  REAL,   -- AI's prediction
            actual_hours        REAL,   -- filled in when task is marked done
            ai_reasoning        TEXT,   -- shown to user: "Based on similar tasks..."
            ai_tags             TEXT DEFAULT '[]',  -- JSON array for pattern matching
            ai_confidence       REAL,   -- 0.0 to 1.0, how confident the AI was

            -- Snapshot of AI context when estimate was made.
            -- Lets us see WHY the AI made a decision even months later.
            context_snapshot    TEXT DEFAULT '{}',

            scheduled_start     TEXT,   -- when AI placed this in the schedule
            scheduled_end       TEXT,

            created_at          TEXT DEFAULT (datetime('now')),
            updated_at          TEXT DEFAULT (datetime('now')),
            completed_at        TEXT    -- null until done
        )
    """)

    # -----------------------------------------------------------------
    # SCHEDULE SLOTS
    # The AI's output — a concrete time-blocked schedule.
    # Separated from tasks so re-optimisation only rewrites slots,
    # not the tasks themselves.
    # -----------------------------------------------------------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS schedule_slots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            start_time  TEXT NOT NULL,
            end_time    TEXT NOT NULL,
            slot_type   TEXT DEFAULT 'work',  -- 'work', 'buffer', 'break'
            -- Which re-optimisation run created this slot
            optimisation_id INTEGER REFERENCES optimisation_log(id),
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    # -----------------------------------------------------------------
    # OPTIMISATION LOG
    # Every time the AI re-plans the schedule, it writes a row here.
    # This powers the "undo" feature and the history viewer.
    # trigger: what caused it — 'early_completion', 'overdue', 'manual'
    # schedule_before/after: full JSON snapshots of slots before and after
    # ai_summary: plain English explanation of what changed and why
    # -----------------------------------------------------------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS optimisation_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger_type    TEXT NOT NULL,
            trigger_task_id INTEGER REFERENCES tasks(id),
            schedule_before TEXT NOT NULL,  -- JSON snapshot
            schedule_after  TEXT NOT NULL,  -- JSON snapshot
            ai_summary      TEXT,           -- "Moved 'Math essay' forward 2hrs because..."
            was_undone      INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # -----------------------------------------------------------------
    # TASK HISTORY
    # Every time a task's status or completion changes, log it.
    # This is the AI's primary learning source — it reads this table
    # to understand how long tasks actually take vs estimates.
    # -----------------------------------------------------------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id         INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            event_type      TEXT NOT NULL,  -- 'created', 'started', 'completed', 'overdue', 'rescheduled'
            completion_pct  INTEGER,
            note            TEXT,           -- optional user note or AI note
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # -----------------------------------------------------------------
    # AI PATTERN MEMORY
    # The AI writes generalised patterns here as it learns from history.
    # e.g. "tasks tagged 'essay' take on average 3.2hrs for this user"
    # This persists across sessions so the AI doesn't start from scratch.
    # -----------------------------------------------------------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS ai_patterns (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type    TEXT NOT NULL,  -- 'task_duration', 'difficulty_bias', 'peak_hours'
            tag             TEXT,           -- which task type this applies to
            observed_value  REAL,           -- e.g. average actual hours
            sample_size     INTEGER,        -- how many tasks this is based on
            confidence      REAL,           -- reliability of this pattern
            raw_data        TEXT DEFAULT '{}',  -- full JSON for complex patterns
            updated_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # -----------------------------------------------------------------
    # NOTIFICATIONS
    # Stores pending alerts for the user.
    # The AI writes here when it detects overdue tasks or schedule changes.
    # -----------------------------------------------------------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            type        TEXT NOT NULL,  -- 'overdue', 'rescheduled', 'suggestion'
            task_id     INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
            message     TEXT NOT NULL,
            is_read     INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialised at", DB_PATH)


# -----------------------------------------------------------------
# HELPER: build a rich context blob for the AI
# Call this before any AI request — it gives the model everything
# it needs to make informed estimates in a single structured object.
# -----------------------------------------------------------------
def get_ai_context() -> dict:
    conn = get_conn()
    c = conn.cursor()

    # User profile
    profile = c.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()

    # Last 20 completed tasks with actual vs estimated hours
    recent_completed = c.execute("""
        SELECT title, ai_tags, difficulty, ai_estimated_hours, actual_hours,
               ai_reasoning, completed_at
        FROM tasks
        WHERE status = 'done' AND actual_hours IS NOT NULL
        ORDER BY completed_at DESC
        LIMIT 20
    """).fetchall()

    # Current pending/in-progress tasks
    active_tasks = c.execute("""
        SELECT id, title, difficulty, deadline, ai_estimated_hours,
               scheduled_start, scheduled_end, completion_pct
        FROM tasks
        WHERE status IN ('pending', 'in_progress')
        ORDER BY deadline ASC
    """).fetchall()

    # AI learned patterns
    patterns = c.execute("""
        SELECT pattern_type, tag, observed_value, sample_size, confidence
        FROM ai_patterns
        ORDER BY confidence DESC
    """).fetchall()

    # Overdue tasks
    overdue = c.execute("""
        SELECT id, title, deadline, ai_estimated_hours
        FROM tasks
        WHERE status != 'done' AND deadline < datetime('now')
    """).fetchall()

    conn.close()

    return {
        "user": dict(profile) if profile else {},
        "recent_completed": [dict(r) for r in recent_completed],
        "active_tasks": [dict(t) for t in active_tasks],
        "learned_patterns": [dict(p) for p in patterns],
        "overdue_tasks": [dict(o) for o in overdue],
        "generated_at": datetime.now().isoformat()
    }


# -----------------------------------------------------------------
# HELPER: update AI patterns after a task is completed
# Call this whenever actual_hours is recorded on a task.
# -----------------------------------------------------------------
def update_ai_patterns(task_id: int):
    conn = get_conn()
    c = conn.cursor()

    task = c.execute("""
        SELECT ai_tags, difficulty, ai_estimated_hours, actual_hours
        FROM tasks WHERE id = ?
    """, (task_id,)).fetchone()

    if not task or not task["actual_hours"]:
        conn.close()
        return

    tags = json.loads(task["ai_tags"] or "[]")

    for tag in tags:
        existing = c.execute("""
            SELECT id, observed_value, sample_size
            FROM ai_patterns
            WHERE pattern_type = 'task_duration' AND tag = ?
        """, (tag,)).fetchone()

        if existing:
            # Rolling average
            new_sample = existing["sample_size"] + 1
            new_avg = ((existing["observed_value"] * existing["sample_size"])
                       + task["actual_hours"]) / new_sample
            confidence = min(0.95, new_sample / 10)  # caps at 0.95 after 10 samples

            c.execute("""
                UPDATE ai_patterns
                SET observed_value = ?, sample_size = ?, confidence = ?,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (new_avg, new_sample, confidence, existing["id"]))
        else:
            c.execute("""
                INSERT INTO ai_patterns
                    (pattern_type, tag, observed_value, sample_size, confidence)
                VALUES ('task_duration', ?, ?, 1, 0.1)
            """, (tag, task["actual_hours"]))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()