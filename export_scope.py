"""Resolve the configured export scope to a Calibre search expression.

"all"            -> "" (the whole library)
"virtual_library"-> the named virtual library's saved search expression.
A configured-but-missing virtual library raises, so the export reports an error
rather than silently widening to the full catalog.
"""


class ExportScopeError(Exception):
    """The configured export scope cannot be resolved."""


def _virtual_libraries(db):
    api = getattr(db, "new_api", db)
    try:
        return dict(api.pref("virtual_libraries", {}) or {})
    except Exception:
        return {}


def resolve_search(db, prefs):
    mode = prefs.get("export_mode", "all")
    if mode != "virtual_library":
        return ""
    name = prefs.get("export_virtual_library", "")
    vls = _virtual_libraries(db)
    if name not in vls:
        raise ExportScopeError(
            f"Virtual library {name!r} not found. Choose one in ShelfBridge "
            f"settings or switch to the entire library."
        )
    return vls[name]
