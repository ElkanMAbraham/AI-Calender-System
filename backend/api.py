# backend/api.py
# Public methods on this class are callable from JS as:
#   window.pywebview.api.<method>(args)
# All methods must return a JSON-serialisable value.
#
# api.py is the only module the JS layer talks to. It owns the merge/mapping
# rules for the user profile and delegates raw storage to backend.user_profile
# (JSON) and backend.database (SQLite).
#
# Response envelope: every method returns one of:
#     {"ok": True,  "data": <value>}     on success
#     {"ok": False, "error": "<msg>"}    on failure
# The JS side already speaks this shape (see settings methods in app.js).
#
# Connection management: each method that touches the DB opens its own
# short-lived connection via `get_conn()` and closes it in a `finally`.
# No shared cached connection — pywebview may invoke api methods from
# different JS threads, and a per-call open/close is the simplest safe
# model (matches project-db-decisions).

import json

from backend import database, user_profile


class Api:
    def __init__(self):
        self._window = None

    def set_window(self, window):
        """Called by main.py after the window is created.
        Lets Api push data back to JS via self._window.evaluate_js() if needed."""
        self._window = window

    # ========== Settings ==========
    # The settings/preferences layer predates the database package and
    # lives in user_profile.py (JSON in AppData). Kept as-is — the new
    # CRUD methods below don't touch this.

    # ------ CREATE / UPDATE ------

    def savePreferences(self, payload):
        """
        Saves user preferences to the JSON file.
        Works for both onboarding (first create) and settings page (update).

        Expected payload keys (all optional except where noted):
            name                    str
            primary_use             str  ('work' | 'study' | 'personal' | 'mix')
            primary_use_context     str  (free-form, may be empty)
            ai_provider             str  ('openai' | 'anthropic' | 'ollama')
            default_model           str  (e.g. 'gpt-4o', 'claude-3-5-sonnet-latest')
            autonomy_level          str  ('ask' | 'notify' | 'autonomous')
            api_keys                dict { provider: { 'key': '...' } }
        """
        try:
            existing = user_profile.load_preferences()

            # Merge api_keys so editing one provider doesn't blank out others.
            # The frontend always sends the full map it knows about; we layer
            # incoming on top of what's already on disk.
            existing_keys = existing.get("api_keys", {}) or {}
            incoming_keys = payload.get("api_keys") or {}
            merged_keys = {**existing_keys, **incoming_keys}

            merged = {
                "name": payload.get("name", existing.get("name")),
                "primary_use": payload.get("primary_use", existing.get("primary_use")),
                "primary_use_context": payload.get(
                    "primary_use_context",
                    existing.get("primary_use_context", ""),
                ),
                "ai_provider": payload.get("ai_provider", existing.get("ai_provider")),
                "default_model": payload.get(
                    "default_model",
                    existing.get("default_model", ""),
                ),
                "autonomy_level": payload.get(
                    "autonomy_level",
                    existing.get("autonomy_level"),
                ),
                "api_keys": merged_keys,
            }
            user_profile.save_preferences(merged)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------ READ ------

    def getPreferences(self):
        """
        Retrieves the saved preferences.
        Called from the frontend to pre-fill forms (e.g., onboarding or settings page).
        """
        try:
            prefs = user_profile.load_preferences()
            # Backfill defaults so older settings.json files don't crash the UI.
            prefs.setdefault("api_keys", {})
            prefs.setdefault("primary_use_context", "")
            prefs.setdefault("default_model", "")
            return {"ok": True, "data": prefs}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------ DELETE API KEY ------

    def deleteApiKey(self, provider: str) -> dict:
        """
        Removes the saved API key for one provider.
        The frontend calls this when the user clicks Delete on a key card.
        """
        try:
            prefs = user_profile.load_preferences()
            keys = prefs.get("api_keys", {}) or {}
            if provider not in keys:
                return {"ok": False, "error": "No key for that provider"}
            del keys[provider]
            prefs["api_keys"] = keys
            user_profile.save_preferences(prefs)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ========== Tasks ==========
    # The "intent" half: a task says WHAT needs to be done and roughly
    # HOW LONG, with no scheduling info. The AI consumes these.

    def listTasks(self, status=None, topic=None, limit=None):
        return self._call(database.list_tasks, status=status, topic=topic, limit=limit)

    def getTask(self, id):
        return self._call(database.get_task, id=id)

    def createTask(self, payload):
        # The frontend sends a flat dict matching the task columns. We
        # forward it as kwargs to create_task. Unknown keys are ignored
        # by Python's **kwargs, so a sloppy payload doesn't blow up.
        return self._call(database.create_task, **payload)

    def updateTask(self, id, payload):
        return self._call(database.update_task, id=id, **payload)

    def deleteTask(self, id):
        return self._call(database.delete_task, id=id)

    # ========== Fixed events ==========
    # Immutable calendar entries the AI must schedule around.

    def listFixedEvents(self, start_after=None, end_before=None, limit=None):
        return self._call(
            database.list_fixed_events,
            start_after=start_after,
            end_before=end_before,
            limit=limit,
        )

    def getFixedEvent(self, id):
        return self._call(database.get_fixed_event, id=id)

    def createFixedEvent(self, payload):
        return self._call(database.create_fixed_event, **payload)

    def updateFixedEvent(self, id, payload):
        return self._call(database.update_fixed_event, id=id, **payload)

    def deleteFixedEvent(self, id):
        return self._call(database.delete_fixed_event, id=id)

    # ========== Schedule blocks ==========
    # The AI's current plan. The frontend's calendar view reads from here.

    def listScheduleBlocks(
        self, task_id=None, status=None, start_after=None, end_before=None, limit=None
    ):
        return self._call(
            database.list_schedule_blocks,
            task_id=task_id,
            status=status,
            start_after=start_after,
            end_before=end_before,
            limit=limit,
        )

    def getScheduleBlock(self, id):
        return self._call(database.get_schedule_block, id=id)

    def createScheduleBlock(self, payload):
        return self._call(database.create_schedule_block, **payload)

    def updateScheduleBlock(self, id, payload):
        return self._call(database.update_schedule_block, id=id, **payload)

    def deleteScheduleBlock(self, id):
        return self._call(database.delete_schedule_block, id=id)

    # ========== Task completion log ==========
    # Behavioural record. Write-mostly in practice.

    def listCompletions(
        self, task_id=None, topic=None, since=None, until=None, limit=None
    ):
        return self._call(
            database.list_completions,
            task_id=task_id,
            topic=topic,
            since=since,
            until=until,
            limit=limit,
        )

    def getCompletion(self, id):
        return self._call(database.get_completion, id=id)

    def logCompletion(self, payload):
        return self._call(database.log_completion, **payload)

    def updateCompletion(self, id, payload):
        return self._call(database.update_completion, id=id, **payload)

    def deleteCompletion(self, id):
        return self._call(database.delete_completion, id=id)

    # ========== User productivity curve ==========
    # Aggregate: efficiency per (day_of_week, hour_of_day). Composite PK.

    def listProductivity(self):
        return self._call(database.list_productivity)

    def getProductivity(self, day_of_week, hour_of_day):
        return self._call(
            database.get_productivity,
            day_of_week=day_of_week,
            hour_of_day=hour_of_day,
        )

    def upsertProductivity(self, day_of_week, hour_of_day, efficiency_score):
        return self._call(
            database.upsert_productivity,
            day_of_week=day_of_week,
            hour_of_day=hour_of_day,
            efficiency_score=efficiency_score,
        )

    def deleteProductivity(self, day_of_week, hour_of_day):
        return self._call(
            database.delete_productivity,
            day_of_week=day_of_week,
            hour_of_day=hour_of_day,
        )

    # ========== User topic efficiency ==========
    # Per-topic speed multiplier. PK is the topic string.

    def listTopicEfficiencies(self):
        return self._call(database.list_topic_efficiencies)

    def getTopicEfficiency(self, topic):
        return self._call(database.get_topic_efficiency, topic=topic)

    def upsertTopicEfficiency(self, topic, efficiency_multiplier):
        return self._call(
            database.upsert_topic_efficiency,
            topic=topic,
            efficiency_multiplier=efficiency_multiplier,
        )

    def deleteTopicEfficiency(self, topic):
        return self._call(database.delete_topic_efficiency, topic=topic)

    # ========== Task event log ==========
    # Full audit trail for scheduling events and status changes.

    def listEvents(self, task_id=None, event_type=None, since=None, limit=None):
        return self._call(
            database.list_events,
            task_id=task_id,
            event_type=event_type,
            since=since,
            limit=limit,
        )

    def getEvent(self, id):
        return self._call(database.get_event, id=id)

    def logEvent(self, payload):
        return self._call(database.log_event, **payload)

    def updateEvent(self, id, payload):
        return self._call(database.update_event, id=id, **payload)

    def deleteEvent(self, id):
        return self._call(database.delete_event, id=id)

    # ========== Internal ==========

    def _call(self, fn, **kwargs):
        """
        Open a DB connection, run `fn(conn, **kwargs)`, close the
        connection, and wrap the result in the standard envelope.

        Used by every CRUD method on this class. Settings methods
        (savePreferences / getPreferences / deleteApiKey) bypass this
        because they talk to the JSON profile store, not the DB.
        """
        conn = database.get_conn()
        try:
            data = fn(conn, **kwargs)
            # json.dumps is a smoke test: it raises TypeError if anything
            # in the result isn't JSON-serialisable (e.g. a leftover
            # sqlite3.Row, datetime, etc.). We don't need the string
            # itself — pywebview re-serialises on the way out — but
            # catching the error here gives a better message than a
            # late pywebview failure.
            json.dumps(data, default=str)
            return {"ok": True, "data": data}
        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            conn.close()
