# src-tauri/python-backend/main.py
import sys
import json
import sqlite3

DB_PATH = "../calendar.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def handle_check_onboarding():
    conn = get_conn()
    c = conn.cursor()
    count = c.execute("SELECT COUNT(*) FROM user_profile WHERE id = 1").fetchone()[0]
    conn.close()
    return {"status": "success", "onboarding_done": count > 0}


def handle_save_onboarding(data):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        INSERT OR REPLACE INTO user_profile 
        (id, name, primary_use, ai_provider, ai_api_key, autonomy_level, ai_context, updated_at) 
        VALUES (1, ?, ?, ?, ?, ?, ?, datetime('now'))
    """,
        (
            data.get("name"),
            data.get("primary_use"),
            data.get("ai_provider", "claude"),
            data.get("ai_api_key"),
            data.get("autonomy_level", "notify"),
            data.get("ai_context", "{}"),
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Onboarding completed!"}


def handle_get_profile():
    conn = get_conn()
    c = conn.cursor()
    row = c.execute(
        "SELECT name, primary_use, ai_provider, ai_api_key, autonomy_level, ai_context FROM user_profile WHERE id = 1"
    ).fetchone()
    conn.close()
    if row:
        return {"status": "success", "profile": dict(row)}
    else:
        return {"status": "success", "profile": None}


COMMANDS = {
    "check_onboarding": handle_check_onboarding,
    "save_onboarding": handle_save_onboarding,
    "get_profile": handle_get_profile,
}


def main():
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            command = request.get("command")
            data = request.get("data", {})

            if command in COMMANDS:
                response = COMMANDS[command](data)
            else:
                response = {"status": "error", "message": f"Unknown command: {command}"}

            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"status": "error", "message": str(e)}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
