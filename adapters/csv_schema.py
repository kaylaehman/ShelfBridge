"""Goodreads-import CSV schema — a pure mapping with no I/O.

Extracted so the Goodreads file adapter and the OneDrive upload adapter both
depend on this schema rather than on each other. (review C3: OneDrive previously
reached into ``GoodreadsAdapter._map_book``, a private sibling method.)

StoryGraph accepts this exact format, so it reuses it unchanged.
"""
from html.parser import HTMLParser

GOODREADS_COLUMNS = [
    "Title", "Author", "ISBN", "ISBN13", "My Rating", "Average Rating",
    "Publisher", "Binding", "Number of Pages", "Year Published",
    "Original Publication Year", "Date Read", "Date Added", "Bookshelves",
    "Bookshelves with positions", "Exclusive Shelf", "My Review",
    "Spoiler", "Private Notes", "Read Count", "Owned Copies",
]


class _TagStripper(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def text(self):
        return "".join(self._parts)


def strip_html(value):
    """Strip HTML tags and decode entities using stdlib only. (review M2)"""
    if not value:
        return ""
    parser = _TagStripper()
    try:
        parser.feed(value)
        parser.close()
    except Exception:
        # Malformed markup: fall back to returning what was parsed so far.
        pass
    return parser.text().strip()


def _gr_date(iso_date):
    """Goodreads wants YYYY/MM/DD, not ISO YYYY-MM-DD. (review C4)"""
    if not iso_date:
        return ""
    return str(iso_date)[:10].replace("-", "/")


def goodreads_row(b):
    """Map one BookDict to a Goodreads CSV row dict."""
    rating_calibre = b.get("rating") or 0
    rating_gr = round(rating_calibre / 2) if rating_calibre else 0
    read_dates = b.get("read_dates") or []
    shelf = "read" if (rating_calibre or read_dates) else "to-read"
    review = strip_html(b.get("comments"))
    read_date = _gr_date(read_dates[0] if read_dates else "")

    return {
        "Title": b.get("title", ""),
        "Author": "; ".join(b.get("authors", [])),
        "ISBN": b.get("isbn") or "",
        "ISBN13": b.get("isbn13") or "",
        "My Rating": rating_gr,
        "Average Rating": "",
        "Publisher": b.get("publisher") or "",
        "Binding": "",
        "Number of Pages": "",
        "Year Published": (b.get("pub_date") or "")[:4],
        "Original Publication Year": "",
        "Date Read": read_date,
        "Date Added": "",
        "Bookshelves": ", ".join(b.get("tags", [])),
        "Bookshelves with positions": "",
        "Exclusive Shelf": shelf,
        "My Review": review,
        "Spoiler": "",
        "Private Notes": "",
        "Read Count": str(len(read_dates)) if (shelf == "read" and read_dates) else ("1" if shelf == "read" else ""),
        "Owned Copies": "1",
    }
