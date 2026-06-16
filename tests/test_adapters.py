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


# ── Notion adapter (upsert) ──────────────────────────────────────────────────

def test_notion_validate_prefs():
    from calibre_plugins.shelf_bridge.adapters.notion import NotionAdapter
    errs = NotionAdapter({}).validate_prefs()
    assert any("token" in e for e in errs)
    assert any("database ID" in e for e in errs)


def test_notion_build_properties_omits_null_rating():
    from calibre_plugins.shelf_bridge.adapters.notion import NotionAdapter
    a = NotionAdapter({})
    rated = a._build_properties({"calibre_id": 1, "title": "x", "rating": 10})
    assert rated["Rating"]["number"] == 5
    assert rated["Calibre ID"]["number"] == 1
    unrated = a._build_properties({"calibre_id": 2, "title": "y", "rating": None})
    assert "Rating" not in unrated  # Notion rejects {"number": None}


def test_notion_upsert_patches_existing_creates_new():
    """Stub the _request seam: book 1 exists (PATCH), book 2 is new (POST)."""
    from calibre_plugins.shelf_bridge.adapters.notion import NotionAdapter
    calls = []

    class StubNotion(NotionAdapter):
        def _request(self, method, url, payload=None):
            calls.append((method, url))
            if url.endswith("/query"):
                cid = payload["filter"]["number"]["equals"]
                return {"results": [{"id": "existing-page"}]} if cid == 1 else {"results": []}
            return {"id": "new-page"}

    adapter = StubNotion({"notion_database_id": "db1", "notion_token": "t"})
    books = [
        {"calibre_id": 1, "title": "A", "authors": [], "tags": []},
        {"calibre_id": 2, "title": "B", "authors": [], "tags": []},
    ]
    result = adapter.export(books, {})
    assert result.success and result.records_exported == 2
    methods = [m for m, _ in calls]
    assert "PATCH" in methods  # existing page updated
    assert "POST" in methods   # new page created


# ── Airtable adapter ─────────────────────────────────────────────────────────

def test_airtable_validate_prefs():
    from calibre_plugins.shelf_bridge.adapters.airtable import AirtableAdapter
    errs = AirtableAdapter({}).validate_prefs()
    assert any("Token" in e for e in errs)
    assert any("Base ID" in e for e in errs)


def test_airtable_fields_include_calibre_id():
    from calibre_plugins.shelf_bridge.adapters.airtable import AirtableAdapter
    fields = AirtableAdapter({})._fields({"calibre_id": 7, "title": "x", "rating": 6})
    assert fields["Calibre ID"] == 7
    assert fields["Rating"] == 3


# ── Hardcover adapter ────────────────────────────────────────────────────────

def test_hardcover_skips_books_without_isbn():
    from calibre_plugins.shelf_bridge.adapters.hardcover import HardcoverAdapter
    calls = []

    class StubHC(HardcoverAdapter):
        def _gql(self, query, variables):
            calls.append(variables)
            return {"data": {}}

    adapter = StubHC({"hardcover_token": "t"})
    books = [
        {"calibre_id": 1, "title": "Has ISBN", "isbn13": "9780441013593", "rating": 8},
        {"calibre_id": 2, "title": "No ISBN", "isbn": None, "isbn13": None},
    ]
    result = adapter.export(books, {})
    assert result.records_exported == 1
    assert any("no isbn" in e.lower() for e in result.errors)
    assert calls[0]["status"] == "read"
