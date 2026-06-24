import os
import webview
from backend import database
from backend.api import Api

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

def main() -> None:

    database.init_db()
  
    api = Api()
   
    window = webview.create_window(
        title     = "Docket",
        url       = os.path.join(FRONTEND_DIR, "onboarding.html"),
        js_api    = api,
        width     = 1024,
        height    = 768,
        resizable = True,
    )

  
    api.set_window(window)
    webview.start(debug=True)


if __name__ == "__main__":
    main()