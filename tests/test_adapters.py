"""Adapter tests — pure logic, no network. Loads sample BookDicts from fixtures."""
import csv
import json
import pathlib
import tempfile

FIXTURES = json.loads(
    (pathlib.Path(__file__).parent / "fixtures" / "sample_books.json").read_text(encoding="utf-8")
)


def _tmp_csv():
    f = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    f.close()
    return f.name


# ── csv_schema (pure mapper) ─────────────────────────────────────────────────

def test_goodreads_row_rating_conversion():
    from calibre_plugins.shelf_bridge.adapters.csv_schema import goodreads_row
    assert goodreads_row({"title": "x", "rating": 10})["My Rating"] == 5
    assert goodreads_row({"title": "x", "rating": 8})["My Rating"] == 4
    assert goodreads_row({"title": "x", "rating": None})["My Rating"] == 0


def test_goodreads_row_exclusive_shelf():
    from calibre_plugins.shelf_bridge.adapters.csv_schema import goodreads_row
    assert goodreads_row({"title": "x", "rating": 8})["Exclusive Shelf"] == "read"
    assert goodreads_row({"title": "x", "read_dates": ["2020-01-01"]})["Exclusive Shelf"] == "read"
    assert goodreads_row({"title": "x"})["Exclusive Shelf"] == "to-read"


def test_goodreads_row_date_format_slash():
    from calibre_plugins.shelf_bridge.adapters.csv_schema import goodreads_row
    row = goodreads_row({"title": "x", "read_dates": ["2023-05-01"]})
    assert row["Date Read"] == "2023/05/01"  # not ISO hyphens (review C4)


def test_goodreads_row_strips_html_and_entities():
    from calibre_plugins.shelf_bridge.adapters.csv_schema import goodreads_row
    row = goodreads_row({"title": "x", "comments": "Epic <i>spice</i> &amp; politics"})
    assert row["My Review"] == "Epic spice & politics"


# ── Goodreads adapter ────────────────────────────────────────────────────────

def test_goodreads_csv_roundtrip():
    from calibre_plugins.shelf_bridge.adapters.goodreads import GoodreadsAdapter
    path = _tmp_csv()
    adapter = GoodreadsAdapter({"goodreads_output_path": path})
    result = adapter.export(FIXTURES, {})
    assert result.success
    assert result.records_exported == len(FIXTURES)
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(FIXTURES)
    assert rows[0]["Title"] == "The Pragmatic Programmer"


def test_goodreads_uses_correct_pref_key():
    from calibre_plugins.shelf_bridge.adapters.goodreads import GoodreadsAdapter
    # Wrong key -> empty path -> failed result, not an exception (review C1, M6)
    adapter = GoodreadsAdapter({"output_path": "/nope/x.csv"})
    result = adapter.export(FIXTURES, {})
    assert not result.success
    assert result.errors


def test_goodreads_validate_prefs():
    from calibre_plugins.shelf_bridge.adapters.goodreads import GoodreadsAdapter
    assert GoodreadsAdapter({}).validate_prefs()  # missing path
    errs = GoodreadsAdapter({"goodreads_output_path": "/tmp/out.txt"}).validate_prefs()
    assert any("end in .csv" in e for e in errs)


# ── StoryGraph adapter ───────────────────────────────────────────────────────

def test_storygraph_uses_distinct_path_key():
    from calibre_plugins.shelf_bridge.adapters.storygraph import StoryGraphAdapter
    path = _tmp_csv()
    adapter = StoryGraphAdapter({"storygraph_output_path": path})
    assert adapter._output_path() == path
    result = adapter.export(FIXTURES, {})
    assert result.success and result.records_exported == len(FIXTURES)


# ── Google Sheets adapter ────────────────────────────────────────────────────

def test_google_sheets_validate_prefs():
    import importlib
    importlib.import_module(
        "calibre_plugins.shelf_bridge.auth.credential_store")._keyring_ok = False
    from calibre_plugins.shelf_bridge.adapters.google_sheets import GoogleSheetsAdapter
    errs = GoogleSheetsAdapter({}).validate_prefs()
    assert any("Client ID" in e for e in errs)
    assert any("Client Secret" in e for e in errs)
    assert any("Spreadsheet ID" in e for e in errs)
    assert any("not authorized" in e for e in errs)


def test_google_sheets_rows_header_and_values():
    from calibre_plugins.shelf_bridge.adapters.google_sheets import GoogleSheetsAdapter
    from calibre_plugins.shelf_bridge.adapters.csv_schema import GOODREADS_COLUMNS
    rows = GoogleSheetsAdapter({})._rows([
        {"calibre_id": 1, "title": "Dune", "authors": ["Herbert, Frank"], "rating": 8},
    ])
    assert rows[0] == list(GOODREADS_COLUMNS)         # header row
    assert rows[1][0] == "Dune"                        # Title column value
    assert len(rows[1]) == len(GOODREADS_COLUMNS)


def test_google_sheets_clear_then_write(monkeypatch):
    """Export clears the sheet then writes header+rows (idempotent)."""
    from calibre_plugins.shelf_bridge.adapters.google_sheets import GoogleSheetsAdapter
    import calibre_plugins.shelf_bridge.adapters.google_sheets as gs

    monkeypatch.setattr(gs, "get_valid_token", lambda cid, cs, prefs: "tok")
    calls = []

    class Stub(GoogleSheetsAdapter):
        def _request(self, method, url, token, payload=None):
            calls.append((method, url))
            return {"properties": {"title": "My Sheet"}}

    adapter = Stub({
        "google_client_id": "cid", "google_client_secret": "sec",
        "google_spreadsheet_id": "sheet123",
    })
    result = adapter.export([{"calibre_id": 1, "title": "Dune", "authors": []}], {})
    assert result.success and result.records_exported == 1
    methods = [m for m, _ in calls]
    assert methods == ["POST", "PUT"]                  # clear, then write
    assert any(":clear" in url for _, url in calls)
