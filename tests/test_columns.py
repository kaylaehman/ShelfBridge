from calibre_plugins.shelf_bridge import columns as C


def test_column_value_formats_fields():
    b = {
        "title": "Dune", "authors": ["Herbert, Frank", "Other, A"],
        "tags": ["sci-fi", "fav"], "rating": 8, "isbn13": "978",
        "read_dates": ["2022-01-15"], "publisher": "Ace", "pub_date": "1965-08-01",
        "series": "Dune", "series_index": 1.0, "languages": ["eng"],
        "comments": "<p>hi &amp; bye</p>", "identifiers": {"isbn": "978", "amazon": "B0"},
        "custom_columns": {"#mood": "epic", "#shelf": None},
    }
    assert C.column_value(b, "title") == "Dune"
    assert C.column_value(b, "authors") == "Herbert, Frank; Other, A"
    assert C.column_value(b, "tags") == "sci-fi, fav"
    assert C.column_value(b, "rating") == "4"          # 8/2 = 4 (0-5)
    assert C.column_value(b, "read_dates") == "2022-01-15"
    assert C.column_value(b, "series_index") == "1"
    assert C.column_value(b, "comments") == "hi & bye"  # HTML stripped
    assert C.column_value(b, "identifiers") == "isbn:978, amazon:B0"
    assert C.column_value(b, "#mood") == "epic"
    assert C.column_value(b, "#shelf") == ""
    assert C.column_value({}, "title") == ""


def test_rating_half_step_and_empty():
    assert C.column_value({"rating": 7}, "rating") == "3.5"
    assert C.column_value({"rating": 0}, "rating") == ""
    assert C.column_value({"rating": None}, "rating") == ""


def test_default_columns_shape():
    cols = C.default_columns()
    assert all(set(c) == {"field", "header", "enabled"} for c in cols)
    enabled = [c["field"] for c in cols if c["enabled"]]
    assert enabled[0] == "title"
    assert "isbn13" in enabled and "comments" in enabled


def test_available_fields_includes_custom():
    fields = dict(C.available_fields({"#mood": "Mood", "#shelf": None}))
    assert "title" in fields
    assert fields["#mood"] == "Mood"        # uses display name
    assert fields["#shelf"] == "#shelf"     # falls back to key


def test_resolve_columns_prefers_pref_and_drops_unknown():
    prefs = {"export_columns": [
        {"field": "title", "header": "T", "enabled": True},
        {"field": "#gone", "header": "X", "enabled": True},
    ]}
    cols = C.resolve_columns(prefs, custom_columns={})
    fields = [c["field"] for c in cols]
    assert fields == ["title"]              # #gone dropped (not a known field)


def test_resolve_columns_defaults_when_empty():
    assert C.resolve_columns({"export_columns": []}) == C.default_columns()


def test_build_rows_header_order_and_enabled_only():
    cols = [
        {"field": "title", "header": "Title", "enabled": True},
        {"field": "authors", "header": "Author(s)", "enabled": True},
        {"field": "rating", "header": "Rating", "enabled": False},
    ]
    books = [{"title": "Dune", "authors": ["Herbert, Frank"], "rating": 8}]
    rows = C.build_rows(books, cols)
    assert rows[0] == ["Title", "Author(s)"]            # header, enabled only
    assert rows[1] == ["Dune", "Herbert, Frank"]
