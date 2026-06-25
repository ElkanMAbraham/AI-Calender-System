import os
import webview
import logging
from backend import database
from backend.database import DB_PATH
from backend.api import Api
import sqlite3
import pathlib

logging.getLogger("pywebview").setLevel(logging.CRITICAL)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(BASE_DIR, "frontend")

def page(name):
    return pathlib.Path(os.path.join(FRONTEND, name)).as_uri()

ONBOARDING = page("onboarding.html")
INDEX = page("index.html")


class DesktopApi:
    def __init__(self):
        self.window = None

    def saveOnboarding(self, payload):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                """
                INSERT OR REPLACE INTO user_profile 
                    (id, name, primary_use, ai_provider, autonomy_level)
                VALUES (1, ?, ?, ?, ?)
            """,
                (
                    payload["name"],
                    payload["primary_use"],
                    payload["ai_provider"],
                    payload["autonomy_level"],
                ),
            )
            conn.commit()
            conn.close()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}


def main() -> None:
    database.init_db()

    api = DesktopApi()

    window = webview.create_window(
        title="Docket",
        url=ONBOARDING,
        js_api=api,
        width=1024,
        height=768,
        resizable=True,
    )

    api.window = window
    webview.start()


if __name__ == "__main__":
    main()
