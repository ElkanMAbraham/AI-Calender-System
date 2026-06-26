# backend/user_profile.py
# Owns the on-disk JSON profile store under %APPDATA%\Docket\settings.json.
#
# Two layers of API:
#   - load_all() / save_all(data)  → generic dict I/O (no knowledge of "preferences")
#   - load_preferences() / save_preferences(prefs) → typed helpers that wrap the
#     "preferences" sub-dict, so api.py never has to know about the file shape.
#
# The atomic-write pattern (tempfile + shutil.move) protects against corruption
# if the process is killed mid-write.

import json
import os
import shutil
import tempfile

from appdirs import user_data_dir


# ========== App Metadata ==========

APP_NAME = "Docket"
APP_AUTHOR = "Docket"
SETTINGS_DIR = user_data_dir(APP_NAME, APP_AUTHOR)


# ========== Private file I/O ==========


def _ensure_settings_dir():
    """Create the settings directory if it doesn't exist."""
    os.makedirs(SETTINGS_DIR, exist_ok=True)


def _settings_file_path() -> str:
    return os.path.join(SETTINGS_DIR, "settings.json")


def _load_all_settings() -> dict:
    """
    Read the entire settings.json file.
    Returns an empty dict if the file doesn't exist or is corrupt.
    """
    file_path = _settings_file_path()
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If corrupt, return empty dict (will be overwritten on next save)
            return {}
    return {}


def _save_all_settings(data: dict) -> None:
    """
    Atomically write the entire settings dict to settings.json.
    Uses a temporary file to prevent corruption.
    """
    _ensure_settings_dir()
    file_path = _settings_file_path()

    # Write to a temp file in the same directory, then move atomically
    with tempfile.NamedTemporaryFile('w', dir=SETTINGS_DIR, delete=False, suffix='.tmp') as tf:
        json.dump(data, tf, indent=4)
        temp_path = tf.name
    shutil.move(temp_path, file_path)


# ========== Public API ==========
#
# These two are the only functions api.py (and any future caller) should use.
# The private helpers above exist solely to back them.


def load_all() -> dict:
    """Read the entire settings file as a dict. Returns {} if missing or corrupt."""
    return _load_all_settings()


def save_all(data: dict) -> None:
    """Atomically overwrite the entire settings file."""
    _save_all_settings(data)


def load_preferences() -> dict:
    """Read just the `preferences` sub-dict. Returns {} if absent."""
    return _load_all_settings().get("preferences", {}) or {}


def save_preferences(prefs: dict) -> None:
    """Persist the `preferences` sub-dict without disturbing sibling top-level keys."""
    data = _load_all_settings()
    data["preferences"] = prefs
    _save_all_settings(data)