"""OneDrive adapter validation, registry resolution, and Graph auth tests.

All keyring access is forced to the prefs fallback so nothing touches the real
OS credential store.
"""
import importlib

import pytest


def _force_fallback():
    cs = importlib.import_module("calibre_plugins.shelf_bridge.auth.credential_store")
    cs._keyring = None
    cs._keyring_ok = False
    return cs


# ── OneDrive validate_prefs ──────────────────────────────────────────────────

def test_onedrive_missing_client_id():
    _force_fallback()
    from calibre_plugins.shelf_bridge.adapters.onedrive import OneDriveAdapter
    errors = OneDriveAdapter({}).validate_prefs()
    assert "OneDrive Client ID is required." in errors


def test_onedrive_rejects_path_traversal():
    _force_fallback()
    from calibre_plugins.shelf_bridge.adapters.onedrive import OneDriveAdapter
    errors = OneDriveAdapter({
        "onedrive_client_id": "cid",
        "onedrive_path": "/Calibre/../../secrets.csv",
    }).validate_prefs()
    assert any("traversal" in e or "invalid" in e for e in errors)


def test_onedrive_path_must_be_csv():
    _force_fallback()
    from calibre_plugins.shelf_bridge.adapters.onedrive import OneDriveAdapter
    errors = OneDriveAdapter({
        "onedrive_client_id": "cid", "onedrive_path": "/Calibre/catalog.txt",
    }).validate_prefs()
    assert any("end in .csv" in e for e in errors)


# ── Registry ─────────────────────────────────────────────────────────────────

def test_registry_resolves_all_six():
    _force_fallback()
    from calibre_plugins.shelf_bridge.adapters import get_adapter, list_adapters
    ids = ["goodreads", "storygraph", "notion", "airtable", "hardcover", "onedrive"]
    for sid in ids:
        adapter = get_adapter(sid, {})
        assert adapter.service_id == sid
    assert len(list_adapters()) == 6


def test_registry_unknown_service_raises():
    _force_fallback()
    from calibre_plugins.shelf_bridge.adapters import get_adapter
    with pytest.raises(ValueError):
        get_adapter("nope", {})


# ── Graph token ──────────────────────────────────────────────────────────────

def test_get_valid_token_unauthorized_raises():
    _force_fallback()
    from calibre_plugins.shelf_bridge.auth.graph_token import get_valid_token, AuthExpiredError
    with pytest.raises(AuthExpiredError):
        get_valid_token("cid", {})


def test_poll_for_token_honours_stop_event():
    _force_fallback()
    import threading
    from calibre_plugins.shelf_bridge.auth.graph_token import poll_for_token, AuthExpiredError
    stop = threading.Event()
    stop.set()
    with pytest.raises(AuthExpiredError):
        poll_for_token("cid", "devcode", interval=1, timeout_secs=30, stop_event=stop)
