# backend/api.py
# Public methods on this class are callable from JS as:
#   window.pywebview.api.<method>(args)
# All methods must return a JSON-serialisable value.
#
# api.py is the only module the JS layer talks to. It owns the merge/mapping
# rules for the user profile and delegates raw storage to backend.user_profile
# (JSON) and backend.database (SQLite).

from backend import user_profile


class Api:
    def __init__(self):
        self._window = None

    def set_window(self, window):
        """Called by main.py after the window is created.
        Lets Api push data back to JS via self._window.evaluate_js() if needed."""
        self._window = window

    # ========== Settings ==========

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