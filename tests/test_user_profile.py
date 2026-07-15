# tests/test_user_profile.py
# Tests for backend.user_profile — the JSON settings store.
#
# We use the `settings_dir` fixture from conftest.py to redirect
# SETTINGS_DIR to a temp directory. Without that, the tests would
# touch the user's real %APPDATA%/Docket/settings.json — which the
# permission classifier rightly blocks.

import json

from backend import user_profile


# ========== load_preferences / save_preferences ==========


def test_load_preferences_returns_empty_when_file_missing(settings_dir):
    """No file on disk → empty dict, not an exception."""
    assert user_profile.load_preferences() == {}


def test_save_and_load_preferences_round_trip(settings_dir):
    user_profile.save_preferences({"name": "Anjeriko", "ai_provider": "openai"})
    assert user_profile.load_preferences() == {
        "name": "Anjeriko", "ai_provider": "openai"
    }


def test_save_preferences_overwrites_preferences_subkey(settings_dir):
    """
    save_preferences() should ONLY overwrite the `preferences` sub-dict.
    Sibling top-level keys (if we ever add any) must be preserved.
    """
    user_profile.save_all({"preferences": {"a": 1}, "other": "keep me"})
    user_profile.save_preferences({"b": 2})
    data = user_profile.load_all()
    assert data["other"] == "keep me"
    assert data["preferences"] == {"b": 2}


def test_save_preferences_atomic_no_leftover_tmp(settings_dir):
    """
    The save uses tempfile + shutil.move. Verify no .tmp file is left
    behind after a successful save.
    """
    user_profile.save_preferences({"name": "x"})
    files = list(settings_dir.iterdir())
    assert len(files) == 1
    assert files[0].name == "settings.json"


# ========== load_all / save_all ==========


def test_load_all_returns_empty_when_file_missing(settings_dir):
    assert user_profile.load_all() == {}


def test_save_all_round_trip(settings_dir):
    user_profile.save_all({"a": 1, "b": {"c": 2}})
    assert user_profile.load_all() == {"a": 1, "b": {"c": 2}}


def test_load_all_returns_dict_for_corrupt_file(settings_dir):
    """
    If settings.json exists but is not valid JSON, the loader swallows
    the error and returns {}. This is so the app can still launch and
    let the user fix their settings.
    """
    (settings_dir / "settings.json").write_text("{not valid json")
    assert user_profile.load_all() == {}


def test_load_preferences_returns_empty_for_corrupt_file(settings_dir):
    """Same resilience rule applies to load_preferences."""
    (settings_dir / "settings.json").write_text("totally broken")
    assert user_profile.load_preferences() == {}


def test_load_all_returns_empty_when_preferences_subkey_missing(settings_dir):
    """
    If the file exists but has no 'preferences' key, load_preferences
    must still return {} (not KeyError, not the whole file).
    """
    user_profile.save_all({"some_other_key": "x"})
    assert user_profile.load_preferences() == {}


# ========== settings.json content sanity ==========


def test_settings_file_is_valid_json_after_save(settings_dir):
    """After a save, the file on disk must parse as JSON."""
    user_profile.save_preferences({"name": "Anjeriko"})
    raw = (settings_dir / "settings.json").read_text()
    parsed = json.loads(raw)
    assert parsed == {"preferences": {"name": "Anjeriko"}}
