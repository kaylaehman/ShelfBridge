"""End-to-end integration tests driving the real pipeline.

Calibre is not installed in CI, so this exercises the full chain against a mock
Calibre DB: extract_books -> run_export_headless -> get_adapter ->
credential_store.with_secrets -> real adapter -> real file on disk.
"""
import csv
import datetime
import importlib
import pathlib
import tempfile


# ── Mock Calibre DB (new_api Cache surface used by books.extract_books) ───────

class _Meta:
    def __init__(self, **kw):
        for k in ("title", "publisher", "series", "series_index", "rating",
                  "pubdate", "comments"):
            setattr(self, k, kw.get(k))
        self.authors = kw.get("authors", [])
        self.isbn = kw.get("isbn")
        self.tags = kw.get("tags", [])
        self.languages = kw.get("languages", [])
        self.identifiers = kw.get("identifiers", {})


class _FieldMeta:
    def custom_field_metadata(self):
        return ["#read_date"]


class MockDb:
    def __init__(self):
        self.field_metadata = _FieldMeta()
        self._books = {
            1: _Meta(title="The Pragmatic Programmer", authors=["Hunt, Andrew"],
                     isbn="020161622X", identifiers={"isbn13": "9780201616224"},
                     pubdate=datetime.datetime(1999, 10, 20), tags=["programming"],
                     rating=10, comments="<p>A <b>classic</b> &amp; a must-read.</p>"),
            2: _Meta(title="Untitled Draft", authors=["Doe, Jane"]),
            3: _Meta(title="Dune", authors=["Herbert, Frank"],
                     identifiers={"isbn13": "9780441013593"}, rating=8,
                     pubdate=datetime.datetime(1965, 8, 1), tags=["sci-fi"]),
        }
        self._read = {1: datetime.date(2023, 5, 1)}

    def all_book_ids(self):
        return list(self._books)

    def search(self, q):
        return list(self._books)

    def get_metadata(self, bid, get_cover=False):
        return self._books[bid]

    def field_for(self, col, bid):
        return self._read.get(bid) if col == "#read_date" else None


def _runner_force_fallback():
    er = importlib.import_module("calibre_plugins.shelf_bridge.automation.export_runner")
    cs = importlib.import_module("calibre_plugins.shelf_bridge.auth.credential_store")
    cs._keyring, cs._keyring_ok = None, False   # never touch the real OS keychain
    return er


# ── Full CSV export pipeline ─────────────────────────────────────────────────

def test_end_to_end_goodreads_export_writes_correct_csv():
    er = _runner_force_fallback()
    out = pathlib.Path(tempfile.gettempdir()) / "sb_itest_goodreads.csv"
    if out.exists():
        out.unlink()
    er.prefs.clear()
    er.prefs.update({
        "export_all": True,
        "enabled_services": ["goodreads"],
        "field_maps": {},
        "goodreads_output_path": str(out),
    })

    summary = er.run_export_headless(MockDb(), reason="itest")

    res = summary["results"]["goodreads"]
    assert res["success"] is True
    assert res["records_exported"] == 3
    assert summary["total_books"] == 3
    assert out.exists()

    with open(out, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert [r["Title"] for r in rows] == ["The Pragmatic Programmer", "Untitled Draft", "Dune"]

    pp = rows[0]
    assert pp["My Rating"] == "5"                 # calibre 10 -> GR 5
    assert pp["ISBN13"] == "9780201616224"        # from identifier, not raw isbn
    assert pp["Date Read"] == "2023/05/01"        # YYYY/MM/DD, not ISO
    assert pp["Exclusive Shelf"] == "read"
    assert pp["My Review"] == "A classic & a must-read."   # HTML stripped, entity decoded

    draft = rows[1]
    assert draft["My Rating"] == "0"
    assert draft["Exclusive Shelf"] == "to-read"

    # persisted summary is scrubbed and present
    assert er.prefs["_last_export_summary"]["results"]["goodreads"]["success"] is True
    out.unlink()


def test_end_to_end_field_map_renames_before_adapter():
    """A field_map remaps title -> a new key; adapter still produces a valid CSV."""
    er = _runner_force_fallback()
    out = pathlib.Path(tempfile.gettempdir()) / "sb_itest_fieldmap.csv"
    er.prefs.clear()
    er.prefs.update({
        "export_all": True,
        "enabled_services": ["goodreads"],
        "field_maps": {"goodreads": {"publisher": "Publisher_override"}},
        "goodreads_output_path": str(out),
    })
    summary = er.run_export_headless(MockDb(), reason="itest")
    assert summary["results"]["goodreads"]["success"] is True
    out.unlink(missing_ok=True)


def test_end_to_end_google_sheets_via_runner(monkeypatch):
    """Drive Google Sheets through run_export_headless with a stubbed network seam."""
    er = _runner_force_fallback()
    adapters_mod = importlib.import_module("calibre_plugins.shelf_bridge.adapters")
    import calibre_plugins.shelf_bridge.adapters.google_sheets as gs
    from calibre_plugins.shelf_bridge.adapters.google_sheets import GoogleSheetsAdapter

    monkeypatch.setattr(gs, "get_valid_token", lambda cid, cs, prefs: "tok")
    calls = []

    class StubSheets(GoogleSheetsAdapter):
        def _request(self, method, url, token, payload=None):
            calls.append((method, payload))
            return {}

    orig = adapters_mod._BY_ID["google_sheets"]
    adapters_mod._BY_ID["google_sheets"] = StubSheets
    try:
        er.prefs.clear()
        er.prefs.update({
            "export_all": True,
            "enabled_services": ["google_sheets"],
            "field_maps": {},
            "google_client_id": "cid",
            "google_client_secret": "sec",
            "google_spreadsheet_id": "sheet123",
            # authorized token so validate_prefs passes (keyring forced to fallback)
            "google_token": {"access_token": "a", "refresh_token": "r", "expires_at": 9_999_999_999},
        })
        summary = er.run_export_headless(MockDb(), reason="itest")
    finally:
        adapters_mod._BY_ID["google_sheets"] = orig

    res = summary["results"]["google_sheets"]
    assert res["success"] is True
    assert res["records_exported"] == 3
    # clear (POST) then write (PUT); write payload carries header + 3 book rows.
    assert [m for m, _ in calls] == ["POST", "PUT"]
    write_payload = calls[1][1]
    assert len(write_payload["values"]) == 4   # header + 3 books


# ── Import-graph smoke test (non-Qt modules) ─────────────────────────────────

def test_all_non_qt_modules_import():
    mods = [
        "books", "prefs", "field_mapping",
        "adapters", "adapters.base", "adapters.csv_schema", "adapters.goodreads",
        "adapters.storygraph", "adapters.http",
        "adapters.google_sheets", "adapters.onedrive",
        "auth.credential_store", "auth.graph_token", "auth.google_token", "auth.oauth",
        "automation.export_runner", "automation.trigger",
    ]
    for m in mods:
        try:
            importlib.import_module(f"calibre_plugins.shelf_bridge.{m}")
        except ImportError as e:
            # automation.trigger imports PyQt; tolerate only that.
            if m == "automation.trigger" and ("PyQt" in str(e) or "Qt" in str(e)):
                continue
            raise
