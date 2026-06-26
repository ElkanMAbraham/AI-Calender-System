import os
import sys
import sqlite3
import pathlib
import threading
from concurrent.futures import ThreadPoolExecutor

import webview

from backend import database
from backend.database import DB_PATH


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(BASE_DIR, "frontend")

_executor = ThreadPoolExecutor(max_workers=4)


def page(name):
    return pathlib.Path(os.path.join(FRONTEND, name)).as_uri()


ONBOARDING = page("onboarding.html")
INDEX = page("index.html")


class DesktopApi:
    def __init__(self):
        self._window = None

    def saveOnboarding(self, payload):
        future = _executor.submit(self._saveOnboarding_worker, payload)
        return future.result()

    def _saveOnboarding_worker(self, payload):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO user_profile
                        (id, name, primary_use, ai_provider, ai_api_key, autonomy_level, ai_context)
                    VALUES (1, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["name"],
                        payload["primary_use"],
                        payload["ai_provider"],
                        payload.get("ai_api_key"),
                        payload["autonomy_level"],
                        payload.get("ai_context", "{}"),
                    ),
                )
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def finishOnboarding(self):
        self.window.load_url(INDEX)


def main() -> None:
    threading.Thread(target=database.init_db, daemon=True).start()

    api = DesktopApi()

    window = webview.create_window(
        title="Docket",
        url=ONBOARDING,
        js_api=api,
        width=1024,
        height=768,
        resizable=True,
    )
    api._window = window

    webview.start(gui="edgechromium", debug=False)


if __name__ == "__main__":
    main()
