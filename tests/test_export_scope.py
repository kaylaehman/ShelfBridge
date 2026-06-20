import pytest
from calibre_plugins.shelf_bridge.export_scope import resolve_search, ExportScopeError


class _NewApi:
    def __init__(self, vls):
        self._vls = vls
    def pref(self, key, default=None):
        return self._vls if key == "virtual_libraries" else default


class _Db:
    def __init__(self, vls):
        self.new_api = _NewApi(vls)


def test_all_mode_returns_empty_search():
    db = _Db({"Fiction": "tags:fiction"})
    assert resolve_search(db, {"export_mode": "all"}) == ""
    assert resolve_search(db, {}) == ""                 # default is "all"


def test_virtual_library_resolves_to_expression():
    db = _Db({"Fiction": "tags:fiction", "Read": "#read_date:true"})
    prefs = {"export_mode": "virtual_library", "export_virtual_library": "Fiction"}
    assert resolve_search(db, prefs) == "tags:fiction"


def test_missing_virtual_library_raises():
    db = _Db({"Fiction": "tags:fiction"})
    prefs = {"export_mode": "virtual_library", "export_virtual_library": "Nope"}
    with pytest.raises(ExportScopeError):
        resolve_search(db, prefs)
