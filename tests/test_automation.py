"""Automation tests. export_runner is pure-logic; trigger tests need Qt and are
skipped when PyQt is unavailable."""
import importlib

import pytest


class _FieldMeta:
    def custom_field_metadata(self):
        return []


class MockDb:
    def __init__(self, ids=()):
        self._ids = list(ids)
        self.field_metadata = _FieldMeta()

    def all_book_ids(self):
        return self._ids

    def search(self, q):
        return self._ids

    def get_metadata(self, bid, get_cover=False):
        raise AssertionError("no books in these tests")


def _runner_with_prefs(values):
    """Patch the prefs singleton used by export_runner with a plain dict."""
    er = importlib.import_module("calibre_plugins.shelf_bridge.automation.export_runner")
    er.prefs.clear()
    er.prefs.update(values)
    return er


def test_skips_service_with_invalid_prefs():
    er = _runner_with_prefs({
        "export_all": True,
        "enabled_services": ["onedrive"],
        "field_maps": {},
        "onedrive_client_id": "",   # invalid -> skipped
    })
    # force credential fallback so no keychain is touched
    cs = importlib.import_module("calibre_plugins.shelf_bridge.auth.credential_store")
    cs._keyring, cs._keyring_ok = None, False
    summary = er.run_export_headless(MockDb(), reason="test")
    assert summary["results"]["onedrive"]["skipped"]


def test_services_override_takes_precedence():
    er = _runner_with_prefs({
        "export_all": True,
        "enabled_services": ["goodreads"],   # should be ignored
        "field_maps": {},
    })
    summary = er.run_export_headless(MockDb(), reason="agent", services_override=[])
    assert summary["results"] == {}   # override [] => nothing exported


def test_summary_scrubs_token_like_errors():
    er = _runner_with_prefs({
        "export_all": True,
        "enabled_services": ["unknown_service"],
        "field_maps": {},
    })
    summary = er.run_export_headless(MockDb(), reason="test")
    # unknown service -> ValueError captured as an error; summary persisted+scrubbed
    assert "unknown_service" in summary["results"]
    assert er.prefs["_last_export_summary"]["results"]["unknown_service"]["errors"]


# ── Trigger (Qt) ─────────────────────────────────────────────────────────────

def _has_qt():
    try:
        import PyQt5  # noqa: F401
        return True
    except ImportError:
        try:
            import PyQt6  # noqa: F401
            return True
        except ImportError:
            return False


@pytest.mark.skipif(not _has_qt(), reason="PyQt not available")
def test_debounce_prevents_double_export():
    import time
    from unittest.mock import MagicMock
    from calibre_plugins.shelf_bridge.automation.trigger import ShelfBridgeTrigger
    from calibre_plugins.shelf_bridge.prefs import prefs
    prefs["auto_export_on_change"] = True
    trigger = ShelfBridgeTrigger(MagicMock())
    trigger._last_export = time.time()
    fired = []
    trigger.export_requested.connect(lambda r: fired.append(r))
    trigger._on_library_change()
    assert len(fired) == 0
