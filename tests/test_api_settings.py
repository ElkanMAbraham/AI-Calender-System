# tests/test_api_settings.py
# Tests for the three settings-specific api.py methods:
#   * savePreferences
#   * getPreferences
#   * deleteApiKey
#
# These bypass _call() because they talk to the JSON profile store,
# not the DB. We use the `api` fixture (which monkeypatches SETTINGS_DIR
# to a tmp path) so we never touch the user's real settings.json.

import json


# ========== savePreferences / getPreferences ==========


def test_savePreferences_then_getPreferences_round_trip(api, settings_dir):
    payload = {"name": "Anjeriko", "ai_provider": "openai", "api_keys": {}}
    res = api.savePreferences(payload)
    assert res["ok"] is True

    got = api.getPreferences()
    assert got["ok"] is True
    assert got["data"]["name"] == "Anjeriko"
    assert got["data"]["ai_provider"] == "openai"


def test_savePreferences_merges_api_keys(api):
    """
    The merge rule: existing keys must survive an update that only
    changes one key. If a user has both 'openai' and 'anthropic' keys
    saved and updates just the 'openai' one, 'anthropic' must remain.
    """
    api.savePreferences({"api_keys": {"openai": {"key": "sk-old"}, "anthropic": {"key": "ak-1"}}})
    api.savePreferences({"api_keys": {"openai": {"key": "sk-new"}}})
    got = api.getPreferences()
    assert got["data"]["api_keys"]["openai"]["key"] == "sk-new"
    assert got["data"]["api_keys"]["anthropic"]["key"] == "ak-1"


def test_savePreferences_partial_update_preserves_unchanged_fields(api):
    """A partial payload should merge with the existing preferences."""
    api.savePreferences({"name": "Anjeriko", "ai_provider": "openai"})
    api.savePreferences({"ai_provider": "anthropic"})
    got = api.getPreferences()
    assert got["data"]["name"] == "Anjeriko"  # unchanged
    assert got["data"]["ai_provider"] == "anthropic"  # updated


def test_getPreferences_backfills_defaults(api, settings_dir):
    """
    If settings.json exists but is missing some keys, getPreferences
    should backfill them with defaults so the frontend doesn't crash.
    """
    # Write a minimal file that's missing the new defaults.
    (settings_dir / "settings.json").write_text(
        json.dumps({"preferences": {"name": "x"}})
    )
    got = api.getPreferences()
    assert got["ok"] is True
    assert got["data"]["name"] == "x"
    assert got["data"]["api_keys"] == {}  # backfilled
    assert got["data"]["default_model"] == ""  # backfilled


def test_getPreferences_when_no_file(api, settings_dir):
    """No settings file at all → empty data, ok=True."""
    got = api.getPreferences()
    assert got["ok"] is True
    assert got["data"]["api_keys"] == {}


# ========== deleteApiKey ==========


def test_deleteApiKey_removes_provider(api):
    api.savePreferences({"api_keys": {"openai": {"key": "sk-1"}, "anthropic": {"key": "ak-1"}}})
    res = api.deleteApiKey("openai")
    assert res["ok"] is True
    got = api.getPreferences()
    assert "openai" not in got["data"]["api_keys"]
    assert got["data"]["api_keys"]["anthropic"]["key"] == "ak-1"  # untouched


def test_deleteApiKey_unknown_provider_returns_error_envelope(api):
    """Deleting a key that doesn't exist must NOT silently succeed."""
    res = api.deleteApiKey("ghost-provider")
    assert res["ok"] is False
    assert "error" in res
