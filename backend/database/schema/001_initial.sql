-- 001_initial.sql
-- Initial schema for the Docket app.
-- All 7 tables from the technical handover (§2.1–2.7), plus indexes.
--
-- Conventions:
--   * All ids are TEXT UUIDs.
--   * All timestamps are ISO 8601 UTC ("...Z"), populated by
--     strftime('%Y-%m-%dT%H:%M:%fZ', 'now') so they sort as strings
--     and round-trip cleanly with the rest of the app.

-- -----------------------------------------------------------------
-- TASKS
-- Stores the *intent* — what needs to be done. No scheduling info.
-- -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
    id                          TEXT PRIMARY KEY,
    title                       TEXT NOT NULL,
    estimated_duration_minutes  INTEGER NOT NULL,
    deadline                    TEXT,
    earliest_start              TEXT,
    priority                    INTEGER NOT NULL DEFAULT 3
                                CHECK (priority BETWEEN 1 AND 5),
    topic                       TEXT,
    status                      TEXT NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    recurrence_rule             TEXT,
    created_at                  TEXT NOT NULL
                                DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at                  TEXT NOT NULL
                                DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- -----------------------------------------------------------------
-- FIXED EVENTS
-- Immutable calendar entries the AI must work around.
-- -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fixed_events (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    start_time      TEXT NOT NULL,
    end_time        TEXT NOT NULL,
    recurrence_rule TEXT,
    source          TEXT
);

-- -----------------------------------------------------------------
-- SCHEDULE BLOCKS
-- The current plan. Only rows with status = 'planned' are active.
-- -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schedule_blocks (
    id          TEXT PRIMARY KEY,
    task_id     TEXT NOT NULL
                REFERENCES tasks(id) ON DELETE CASCADE,
    start_time  TEXT NOT NULL,
    end_time    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'planned'
                CHECK (status IN ('planned', 'in_progress', 'completed', 'cancelled')),
    reasoning   TEXT,
    is_pinned   INTEGER NOT NULL DEFAULT 0
                CHECK (is_pinned IN (0, 1)),
    created_at  TEXT NOT NULL
                DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    version     INTEGER NOT NULL DEFAULT 1
);

-- -----------------------------------------------------------------
-- TASK COMPLETION LOG
-- Behavioural record. Written every time a task is finished.
-- No break / interruption fields — those are inferred downstream.
-- -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS task_completion_log (
    id                      TEXT PRIMARY KEY,
    task_id                 TEXT NOT NULL
                            REFERENCES tasks(id),
    completed_at            TEXT NOT NULL,
    actual_duration_minutes INTEGER NOT NULL,
    planned_duration_minutes INTEGER NOT NULL,
    topic                   TEXT NOT NULL,
    start_time              TEXT NOT NULL,
    confidence              REAL NOT NULL DEFAULT 1.0
);

-- -----------------------------------------------------------------
-- USER PRODUCTIVITY CURVE
-- Aggregate: efficiency per (day_of_week, hour_of_day). Rebuilt from
-- task_completion_log. seed_value 1.0 = baseline.
-- -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_productivity_curve (
    day_of_week      INTEGER NOT NULL
                      CHECK (day_of_week BETWEEN 0 AND 6),
    hour_of_day      INTEGER NOT NULL
                      CHECK (hour_of_day BETWEEN 0 AND 23),
    efficiency_score REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (day_of_week, hour_of_day)
);

-- -----------------------------------------------------------------
-- USER TOPIC EFFICIENCY
-- Per-topic speed multiplier. 0.8 = 20% faster than estimate.
-- -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_topic_efficiency (
    topic                TEXT PRIMARY KEY,
    efficiency_multiplier REAL NOT NULL DEFAULT 1.0,
    last_updated         TEXT NOT NULL
                         DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- -----------------------------------------------------------------
-- TASK EVENT LOG
-- Full audit trail for every scheduling event and status change.
-- -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS task_event_log (
    id          TEXT PRIMARY KEY,
    task_id     TEXT NOT NULL
                REFERENCES tasks(id),
    event_type  TEXT NOT NULL
                CHECK (event_type IN ('scheduled', 'rescheduled', 'status_change', 'completed', 'cancelled', 'manually_moved')),
    old_value   TEXT,
    new_value   TEXT,
    reason      TEXT,
    created_at  TEXT NOT NULL
                DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- -----------------------------------------------------------------
-- INDEXES
-- Cheap to create now, painful to backfill on a populated DB later.
-- -----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_tasks_status
    ON tasks(status);

CREATE INDEX IF NOT EXISTS idx_tasks_deadline
    ON tasks(deadline)
    WHERE deadline IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_schedule_blocks_task
    ON schedule_blocks(task_id);

CREATE INDEX IF NOT EXISTS idx_schedule_blocks_time
    ON schedule_blocks(start_time, end_time)
    WHERE status = 'planned';

CREATE INDEX IF NOT EXISTS idx_completion_log_task
    ON task_completion_log(task_id);

CREATE INDEX IF NOT EXISTS idx_completion_log_completed_at
    ON task_completion_log(completed_at);

CREATE INDEX IF NOT EXISTS idx_event_log_task
    ON task_event_log(task_id, created_at);

CREATE INDEX IF NOT EXISTS idx_fixed_events_time
    ON fixed_events(start_time, end_time);
