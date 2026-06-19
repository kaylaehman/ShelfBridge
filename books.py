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

    # Read every custom column ONCE across all books (bulk), instead of one
    # field_for() call per (book x column). Falls back to per-book reads when
    # the bulk API is unavailable (e.g. simple test mocks).
    custom_fields = list(db.field_metadata.custom_field_metadata())
    custom_by_id = _bulk_custom(db, custom_fields, ids)

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
        custom = custom_by_id.get(bid, {})
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
            "read_dates":     _fmt_dates(custom.get("#read_date")),
            "languages":      list(mi.languages or []),
            "identifiers":    identifiers,
            "comments":       mi.comments,
            "custom_columns": custom,
        })
    return books


def _fmt_dates(val):
    """Format a date-like custom value as a list of ISO date strings."""
    return [val.isoformat()] if val else []


def _bulk_custom(db, fields, ids):
    """Return ``{book_id: {field: value}}`` for every custom field, in bulk."""
    result = {bid: {} for bid in ids}
    for field in fields:
        for bid, val in _bulk_field(db, field, ids).items():
            if bid in result:
                result[bid][field] = val
    return result


def _bulk_field(db, field, ids):
    """Read one field for many books at once.

    Uses Calibre's ``all_field_for`` when present (one query per field);
    otherwise falls back to per-book ``field_for`` so test mocks keep working.
    """
    getter = getattr(db, "all_field_for", None)
    if getter is not None:
        try:
            return dict(getter(field, ids) or {})
        except Exception:
            pass
    out = {}
    for bid in ids:
        try:
            out[bid] = db.field_for(field, bid)
        except Exception:
            pass
    return out
