import os
import pathlib
import threading

import webview

from backend import database
from backend.api import Api
import sqlite3

# ========== App Metadata ==========

APP_NAME = "Docket"
APP_AUTHOR = "Docket"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(BASE_DIR, "frontend")
DB_PATH = "./docket.db"


def page(name):
    """Convert a frontend file path to a file:// URI."""
    return pathlib.Path(os.path.join(FRONTEND, name)).as_uri()


def is_onboarded() -> bool:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT id FROM user_profile WHERE id = 1").fetchone()
            return row is not None
    except:
        return False


ONBOARDING = page("onboarding.html")
INDEX = page("index.html")
TASK = page("task.html")


def main() -> None:
    threading.Thread(target=database.init_db, daemon=True).start()

    api = Api()

    start_url = INDEX if is_onboarded() else ONBOARDING

    window = webview.create_window(
        title="Docket",
        url=start_url,
        js_api=api,
        width=1024,
        height=768,
        resizable=True,
    )
    api.set_window(window)

    webview.start(gui="edgechromium", debug=False)


if __name__ == "__main__":
    main()
