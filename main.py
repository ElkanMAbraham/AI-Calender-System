import os
from backend import database
from backend.api import Api
import threading
from flask import Flask, render_template, jsonify
import webview

app = Flask(__name__, template_folder="frontend", static_folder="frontend/static")


# --- Flask Web Routes ---
@app.route("/")
def index():
    return render_template("onboarding.html")


# --- Flask API Endpoints ---
@app.route("/api/data")
def get_data():
    return jsonify(
        {"status": "Success", "message": "Data retrieved from Flask backend!"}
    )


def start_flask():
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()

    webview.create_window(
        title="Flask + pywebview App",
        url="http://127.0.0.1:5000",
        width=1000,
        height=750,
    )

    webview.start()
