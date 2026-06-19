"""Tests for books.extract_books against a mock Calibre DB."""
import datetime


class _Meta:
    def __init__(self, **kw):
        self.title = kw.get("title")
        self.authors = kw.get("authors", [])
        self.isbn = kw.get("isbn")
        self.publisher = kw.get("publisher")
        self.pubdate = kw.get("pubdate")
        self.tags = kw.get("tags", [])
        self.series = kw.get("series")
        self.series_index = kw.get("series_index")
        self.rating = kw.get("rating")
        self.languages = kw.get("languages", [])
        self.identifiers = kw.get("identifiers", {})
        self.comments = kw.get("comments")


class _FieldMeta:
    def custom_field_metadata(self):
        return ["#read_date", "#shelf"]


class MockDb:
    def __init__(self, books):
        self._books = books  # {id: _Meta}
        self.field_metadata = _FieldMeta()
        self._read_dates = {}

    def all_book_ids(self):
        return list(self._books)

    def search(self, q):
        return list(self._books)

    def get_metadata(self, bid, get_cover=False):
        return self._books[bid]

    def field_for(self, col, bid):
        if col == "#read_date":
            return self._read_dates.get(bid)
        return None


def _db():
    db = MockDb({
        1: _Meta(
            title="The Pragmatic Programmer",
            authors=["Hunt, Andrew"],
            isbn="020161622X",
            pubdate=datetime.datetime(1999, 10, 20),
            tags=["programming"],
            rating=10,
            identifiers={"isbn13": "9780201616224"},
            comments="<p>classic</p>",
        ),
        2: _Meta(title=None, authors=[]),
    })
    db._read_dates[1] = datetime.date(2023, 5, 1)
    return db


def test_extract_books_schema_keys():
    from calibre_plugins.shelf_bridge.books import extract_books
    books = extract_books(_db())
    assert len(books) == 2
    expected = {
        "calibre_id", "title", "authors", "isbn", "isbn13", "publisher",
        "pub_date", "tags", "series", "series_index", "rating", "read_dates",
        "languages", "identifiers", "custom_columns", "comments",
    }
    assert expected <= set(books[0])


def test_isbn13_prefers_identifier_not_raw_isbn():
    from calibre_plugins.shelf_bridge.books import extract_books
    book = extract_books(_db())[0]
    # raw isbn is ISBN-10; isbn13 must come from the identifier
    assert book["isbn"] == "020161622X"
    assert book["isbn13"] == "9780201616224"


def test_read_dates_and_untitled_fallback():
    from calibre_plugins.shelf_bridge.books import extract_books
    books = extract_books(_db())
    assert books[0]["read_dates"] == ["2023-05-01"]
    assert books[1]["title"] == "Untitled"


def test_extract_books_uses_bulk_field_read():
    """When the DB exposes all_field_for, custom columns are read in bulk
    (one query per field) and per-book field_for is never called. (PERF fix)"""
    from calibre_plugins.shelf_bridge.books import extract_books
    calls = {"all": 0}

    class BulkDb(MockDb):
        def all_field_for(self, field, ids):
            calls["all"] += 1
            if field == "#read_date":
                return {1: datetime.date(2023, 5, 1)}
            return {bid: None for bid in ids}

        def field_for(self, col, bid):  # must NOT be called on the bulk path
            raise AssertionError("per-book field_for called despite all_field_for")

    db = BulkDb({1: _Meta(title="x", authors=["A"]), 2: _Meta(title="y", authors=[])})
    books = extract_books(db)
    # field_metadata exposes 2 custom fields -> 2 bulk queries, 0 per-book reads
    assert calls["all"] == 2
    assert books[0]["read_dates"] == ["2023-05-01"]
    assert books[1]["read_dates"] == []
    assert books[1]["read_dates"] == []
