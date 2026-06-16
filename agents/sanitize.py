"""Defense-in-depth sanitization for agent tool I/O.

Book metadata (titles, authors, comments imported from arbitrary websites) flows
into ``list_books`` output and therefore into the LLM context — a prompt-
injection surface. AIDefence is MCP-only and cannot run inside Calibre, so this
is the in-process replacement it recommended: HTML stripping, field truncation,
injection-pattern flagging, and a hard book cap.
"""
import re

from calibre_plugins.shelf_bridge.adapters.csv_schema import strip_html

MAX_BOOKS_TO_LLM = 200

_FIELD_MAX = {
    "title": 300,
    "publisher": 200,
    "series": 200,
    "comments": 1000,
}
_LIST_FIELD_MAX = {
    "authors": 10,
    "tags": 30,
}

_INJECTION_PATTERNS = [
    re.compile(r"(?is)(ignore|disregard|forget|override)\s+(all\s+|the\s+|your\s+|previous\s+|above\s+)*(instruction|rule|prompt)"),
    re.compile(r"(?is)(system\s*prompt|you\s+are\s+now|new\s+instructions?)"),
    re.compile(r"(?is)shelf_bridge\.(set_pref|export|test_connection)"),
    re.compile(r"<\|.*?\|>"),
    re.compile(r"\[/?INST\]|<</?SYS>>"),
]


def _flag(text, field):
    for pat in _INJECTION_PATTERNS:
        if pat.search(text):
            return f"[CONTENT SUPPRESSED: suspicious pattern in {field}]"
    return text


def sanitize_book_for_llm(book):
    """Return a copy of ``book`` safe to place in LLM context."""
    safe = {
        "calibre_id": book.get("calibre_id"),
        "isbn": book.get("isbn"),
        "isbn13": book.get("isbn13"),
        "rating": book.get("rating"),
        "read_dates": book.get("read_dates", []),
    }
    for field, cap in _FIELD_MAX.items():
        val = book.get(field)
        if field == "comments":
            val = strip_html(val)
        if isinstance(val, str):
            val = _flag(val[:cap], field)
        safe[field] = val
    for field, cap in _LIST_FIELD_MAX.items():
        vals = book.get(field, []) or []
        safe[field] = [_flag(str(v)[:200], field) for v in vals[:cap]]
    # custom_columns / raw identifiers are arbitrary user data — drop them.
    return safe


def sanitize_books(books):
    """Sanitize + cap a list of books for the LLM. Returns a dict when capped."""
    sanitized = [sanitize_book_for_llm(b) for b in books]
    if len(sanitized) > MAX_BOOKS_TO_LLM:
        return {
            "truncated": True,
            "total": len(sanitized),
            "returned": MAX_BOOKS_TO_LLM,
            "books": sanitized[:MAX_BOOKS_TO_LLM],
            "hint": "Use the 'search' parameter to narrow results.",
        }
    return sanitized
