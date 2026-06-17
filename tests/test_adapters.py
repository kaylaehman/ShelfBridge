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
