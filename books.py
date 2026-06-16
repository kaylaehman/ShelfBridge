"""Calibre DB -> normalized BookDict dicts.

This is the ONLY module that talks to the Calibre database. Adapters consume the
dicts produced here and must never touch ``db`` directly.
"""
from calibre.db.cache import Cache


def extract_books(db, search=""):
    """Return books from the Calibre library as a list of BookDict dicts.

    ``search`` is an optional Calibre search string (e.g. ``tags:fiction``).
    """
    ids = db.search(search) if search else db.all_book_ids()
    books = []
    for bid in ids:
        mi = db.get_metadata(bid, get_cover=False)
        identifiers = dict(mi.identifiers or {})
        # ISBN-13 lives under the "isbn13" identifier in newer Calibre, "isbn"
        # in older versions; mi.isbn is the raw field and may be ISBN-10, so it
        # is only the last resort. (review C3)
        isbn13 = (
            identifiers.get("isbn13")
            or identifiers.get("isbn")
            or mi.isbn
        )
        books.append({
            "calibre_id":     bid,
            "title":          mi.title or "Untitled",
            "authors":        list(mi.authors or []),
            "isbn":           mi.isbn,
            "isbn13":         isbn13,
            "publisher":      mi.publisher,
            "pub_date":       mi.pubdate.date().isoformat() if mi.pubdate else None,
            "tags":           list(mi.tags or []),
            "series":         mi.series,
            "series_index":   mi.series_index,
            "rating":         mi.rating,
            "read_dates":     _get_custom(db, bid, "#read_date"),
            "languages":      list(mi.languages or []),
            "identifiers":    identifiers,
            "comments":       mi.comments,
            "custom_columns": _all_custom(db, bid),
        })
    return books


def _get_custom(db, bid, col):
    try:
        val = db.field_for(col, bid)
        return [val.isoformat()] if val else []
    except Exception:
        return []


def _all_custom(db, bid):
    # PERF: O(books * custom_columns) field_for() calls. Acceptable for v0.1;
    # switch to a bulk field read if large libraries become slow.
    result = {}
    for col in db.field_metadata.custom_field_metadata():
        try:
            result[col] = db.field_for(col, bid)
        except Exception:
            pass
    return result
