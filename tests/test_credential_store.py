"""Credential store tests — exercise the prefs fallback path deterministically.

We force the keyring backend off so tests never touch the real OS credential
store (which would prompt or persist real secrets on the test machine).
"""
import importlib


def _store_with_fallback():
    cs = importlib.import_module("calibre_plugins.shelf_bridge.auth.credential_store")
    cs._keyring = None
    cs._keyring_ok = False  # force the prefs fallback, skip OS keychain
    return cs


def test_set_and_get_secret_fallback():
    cs = _store_with_fallback()
    prefs = {}
    cs.set_secret("notion_token", "secret-abc", prefs)
    assert prefs["notion_token"] == "secret-abc"
    assert cs.get_secret("notion_token", prefs) == "secret-abc"


def test_json_blob_roundtrip_fallback():
    cs = _store_with_fallback()
    prefs = {}
    blob = {"access_token": "a", "refresh_token": "r", "expires_at": 123}
    cs.set_secret("onedrive_token", blob, prefs)
    assert cs.get_secret("onedrive_token", prefs) == blob


def test_missing_secret_returns_empty():
    cs = _store_with_fallback()
    assert cs.get_secret("hardcover_token", {}) == ""
    assert cs.get_secret("onedrive_token", {}) == {}


def test_with_secrets_overlays_resolved_values():
    cs = _store_with_fallback()
    prefs = {"notion_token": "", "notion_database_id": "db1"}
    cs.set_secret("notion_token", "tok", prefs)
    merged = cs.with_secrets(prefs)
    assert merged["notion_token"] == "tok"
    assert merged["notion_database_id"] == "db1"


def test_delete_secret_fallback():
    cs = _store_with_fallback()
    prefs = {}
    cs.set_secret("airtable_token", "x", prefs)
    cs.delete_secret("airtable_token", prefs)
    assert "airtable_token" not in prefs
