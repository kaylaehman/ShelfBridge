"""Shared-creds fallback: adapters use the user's pref, else the bundled app."""
import importlib

import pytest


def _oauth():
    return importlib.import_module("calibre_plugins.shelf_bridge.oauth_apps")


def _force_cred_fallback():
    cs = importlib.import_module("calibre_plugins.shelf_bridge.auth.credential_store")
    cs._keyring, cs._keyring_ok = None, False


# ── resolver precedence ──────────────────────────────────────────────────────

def test_resolver_prefers_user_value(monkeypatch):
    o = _oauth()
    monkeypatch.setattr(o, "ONEDRIVE_CLIENT_ID", "bundled-cid")
    assert o.onedrive_client_id("my-own") == "my-own"     # user wins
    assert o.onedrive_client_id("") == "bundled-cid"      # falls back
    assert o.onedrive_client_id("   ") == "bundled-cid"   # whitespace -> fallback


def test_has_bundled_flags(monkeypatch):
    o = _oauth()
    monkeypatch.setattr(o, "ONEDRIVE_CLIENT_ID", "")
    assert o.has_bundled_onedrive() is False
    monkeypatch.setattr(o, "ONEDRIVE_CLIENT_ID", "x")
    assert o.has_bundled_onedrive() is True
    monkeypatch.setattr(o, "GOOGLE_CLIENT_ID", "g")
    monkeypatch.setattr(o, "GOOGLE_CLIENT_SECRET", "")
    assert o.has_bundled_google() is False
    monkeypatch.setattr(o, "GOOGLE_CLIENT_SECRET", "s")
    assert o.has_bundled_google() is True


# ── OneDrive adapter fallback ────────────────────────────────────────────────

def test_onedrive_client_id_falls_back_to_bundled(monkeypatch):
    o = _oauth()
    monkeypatch.setattr(o, "ONEDRIVE_CLIENT_ID", "bundled-od")
    from calibre_plugins.shelf_bridge.adapters.onedrive import OneDriveAdapter
    assert OneDriveAdapter({})._client_id() == "bundled-od"
    assert OneDriveAdapter({"onedrive_client_id": "own"})._client_id() == "own"


def test_onedrive_validate_ok_with_bundled_client(monkeypatch):
    _force_cred_fallback()
    o = _oauth()
    monkeypatch.setattr(o, "ONEDRIVE_CLIENT_ID", "bundled-od")
    from calibre_plugins.shelf_bridge.adapters.onedrive import OneDriveAdapter
    errs = OneDriveAdapter({}).validate_prefs()
    assert not any("Client ID is required" in e for e in errs)  # satisfied by bundled


# ── Google Sheets adapter fallback ───────────────────────────────────────────

def test_google_client_creds_fall_back_to_bundled(monkeypatch):
    o = _oauth()
    monkeypatch.setattr(o, "GOOGLE_CLIENT_ID", "bundled-gid")
    monkeypatch.setattr(o, "GOOGLE_CLIENT_SECRET", "bundled-gsec")
    from calibre_plugins.shelf_bridge.adapters.google_sheets import GoogleSheetsAdapter
    a = GoogleSheetsAdapter({})
    assert a._client_id() == "bundled-gid"
    assert a._client_secret() == "bundled-gsec"


def test_google_validate_ok_with_bundled_client(monkeypatch):
    _force_cred_fallback()
    o = _oauth()
    monkeypatch.setattr(o, "GOOGLE_CLIENT_ID", "bundled-gid")
    monkeypatch.setattr(o, "GOOGLE_CLIENT_SECRET", "bundled-gsec")
    from calibre_plugins.shelf_bridge.adapters.google_sheets import GoogleSheetsAdapter
    errs = GoogleSheetsAdapter({"google_spreadsheet_id": "s"}).validate_prefs()
    assert not any("Client ID is required" in e for e in errs)
    assert not any("Client Secret is required" in e for e in errs)


def test_default_constants_empty_means_byo():
    """Shipped default = empty, so behaviour is bring-your-own until filled in."""
    o = _oauth()
    assert o.ONEDRIVE_CLIENT_ID == ""
    assert o.GOOGLE_CLIENT_ID == ""
    assert o.GOOGLE_CLIENT_SECRET == ""
    assert o.has_bundled_onedrive() is False
    assert o.has_bundled_google() is False
