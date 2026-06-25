# backend/api.py
# Public methods on this class are callable from JS as:
#   window.pywebview.api.<method>(args)
# All methods must return a JSON-serialisable value.

from backend import database


class Api:
    def __init__(self):
        self._window = None

    def set_window(self, window):
        """Called by main.py after the window is created.
        Lets Api push data back to JS via self._window.evaluate_js() if needed."""
        self._window = window

    # -----------------------------------------------------------------------
    # Onboarding
    # -----------------------------------------------------------------------

    def save_onboarding(self, payload: dict) -> dict:
        """
        Receives the onboarding form data from JS and writes it to the DB.

        Expected keys:
            name, primary_use, ai_provider, autonomy_level,
            ai_context (JSON string), created_at, updated_at

        Returns:
            { "ok": True }  on success
            { "ok": False, "error": "<message>" }  on failure
        """
        try:
            database.save_user(payload)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}