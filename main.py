import webview
import os
from backend import database
from backend.api import Api

if __name__ == "__main__":
    database.init_db()
    api = Api()

    webview.create_window(
        title = "Docket",
        url = "frontend/index.html",
        js_api = api,
        width = 1024,
        height = 768
    )

    webview.start()