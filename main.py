import os
import pathlib
import threading

import webview

from backend import database
from backend.api import Api


# ========== App Metadata ==========

APP_NAME = "Docket"
APP_AUTHOR = "Docket"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(BASE_DIR, "frontend")


def page(name):
    """Convert a frontend file path to a file:// URI."""
    return pathlib.Path(os.path.join(FRONTEND, name)).as_uri()


ONBOARDING = page("onboarding.html")
INDEX = page("index.html")


def main() -> None:
    threading.Thread(target=database.init_db, daemon=True).start()

    api = Api()

    window = webview.create_window(
        title="Docket",
        url=ONBOARDING,
        js_api=api,
        width=1024,
        height=768,
        resizable=True,
    )
    api.set_window(window)

    webview.start(gui="edgechromium", debug=False)


if __name__ == "__main__":
    main()