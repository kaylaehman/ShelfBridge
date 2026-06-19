"""Configurable export columns (Google Sheets + OneDrive).

Pure logic: which fields are available, how each field formats to a cell string,
and how to build the header + data rows from a column configuration. Mirrors
Calibre's catalog "Fields" selection (include/exclude, order, rename header).
"""
from calibre_plugins.shelf_bridge.adapters.csv_schema import strip_html

# (field_key, default header) for standard BookDict fields, in a natural order.
STANDARD_FIELDS = [
    ("title", "Title"),
    ("authors", "Authors"),
    ("isbn", "ISBN"),
    ("isbn13", "ISBN13"),
    ("publisher", "Publisher"),
    ("pub_date", "Published"),
    ("rating", "Rating"),
    ("tags", "Tags"),
    ("series", "Series"),
    ("series_index", "Series Index"),
    ("read_dates", "Date Read"),
    ("languages", "Languages"),
    ("comments", "Comments"),
    ("identifiers", "Identifiers"),
]

# Fields enabled in the default column set (subset of STANDARD_FIELDS).
_DEFAULT_ENABLED = {
    "title", "authors", "isbn13", "publisher", "pub_date",
    "rating", "tags", "series", "read_dates", "comments",
}


def available_fields(custom_columns=None):
    """Standard fields plus one entry per custom column key."""
    fields = list(STANDARD_FIELDS)
    for key in (custom_columns or {}):
        fields.append((key, _custom_header(key, custom_columns)))
    return fields


def _custom_header(key, custom_columns):
    val = (custom_columns or {}).get(key)
    return val if isinstance(val, str) else key


def default_columns():
    return [
        {"field": f, "header": h, "enabled": f in _DEFAULT_ENABLED}
        for f, h in STANDARD_FIELDS
    ]


def _fmt_rating(val):
    if not val:
        return ""
    stars = val / 2.0
    return str(int(stars)) if stars == int(stars) else str(stars)


def column_value(book, field):
    if field == "authors":
        return "; ".join(book.get("authors") or [])
    if field in ("tags", "languages"):
        return ", ".join(book.get(field) or [])
    if field == "rating":
        return _fmt_rating(book.get("rating"))
    if field == "read_dates":
        dates = book.get("read_dates") or []
        return dates[0] if dates else ""
    if field == "comments":
        return strip_html(book.get("comments"))
    if field == "identifiers":
        ids = book.get("identifiers") or {}
        return ", ".join(f"{k}:{v}" for k, v in ids.items())
    if field.startswith("#"):
        val = (book.get("custom_columns") or {}).get(field)
        if isinstance(val, (list, tuple)):
            return ", ".join(str(v) for v in val)
        return "" if val is None else str(val)
    val = book.get(field)
    if isinstance(val, float) and val == int(val):
        return str(int(val))                 # series_index 1.0 -> "1"
    return "" if val is None else str(val)


def resolve_columns(prefs, custom_columns=None):
    saved = prefs.get("export_columns") or []
    if not saved:
        return default_columns()
    known = {f for f, _ in available_fields(custom_columns)}
    return [dict(c) for c in saved if c.get("field") in known]


def build_rows(books, columns):
    enabled = [c for c in columns if c.get("enabled")]
    rows = [[c["header"] for c in enabled]]
    for b in books:
        rows.append([column_value(b, c["field"]) for c in enabled])
    return rows
