"""Headless export pipeline — shared by automation triggers and the agent.

Differences from the original sketch:
- ``services_override`` lets callers (the agent) pass a service list directly
  instead of mutating the shared ``prefs`` singleton. (review M1/I3)
- Field mapping is applied here, once, before each adapter. (review I1)
- The persisted ``_last_export_summary`` is scrubbed of token-like strings and
  truncated so credentials / API noise do not land in the prefs file. (review M3)
"""
import re

from calibre_plugins.shelf_bridge.books import extract_books
from calibre_plugins.shelf_bridge.adapters import get_adapter
from calibre_plugins.shelf_bridge.export_scope import resolve_search, ExportScopeError
from calibre_plugins.shelf_bridge.prefs import prefs

try:
    from calibre.utils.logging import default_log as log
except Exception:  # pragma: no cover
    class _Log:
        def info(self, *a, **k):
            pass
        warn = warning = error = debug = info
    log = _Log()

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-+/]{24,}={0,2}")


def _scrub_summary(summary):
    import copy
    s = copy.deepcopy(summary)
    for svc in s.get("results", {}).values():
        if isinstance(svc, dict) and svc.get("errors"):
            svc["errors"] = [_TOKEN_RE.sub("[REDACTED]", str(e))[:200] for e in svc["errors"]]
    return s


def run_export_headless(db, reason="manual", services_override=None):
    """Run export for all enabled services without showing any UI.

    Returns a summary dict for logging / agent reporting.
    """
    if services_override is not None:
        services = services_override
    else:
        services = prefs.get("enabled_services", [])
    try:
        search = resolve_search(db, prefs)
    except ExportScopeError as e:
        summary = {"trigger": reason, "total_books": 0,
                   "results": {svc: {"success": False, "errors": [str(e)]}
                               for svc in services}}
        prefs["_last_export_summary"] = _scrub_summary(summary)
        return summary
    books = extract_books(db, search)
    field_maps = prefs.get("field_maps", {})

    summary = {"trigger": reason, "total_books": len(books), "results": {}}

    for svc_id in services:
        try:
            adapter = get_adapter(svc_id, prefs)
        except ValueError as e:
            summary["results"][svc_id] = {"success": False, "errors": [str(e)]}
            continue
        errors = adapter.validate_prefs()
        if errors:
            log.warn(f"[ShelfBridge] Skipping {svc_id}: {errors}")
            summary["results"][svc_id] = {"skipped": True, "reason": errors}
            continue
        try:
            result = adapter.export(books, field_maps.get(svc_id, {}))
            summary["results"][svc_id] = {
                "success": result.success,
                "records_exported": result.records_exported,
                "destination": result.destination,
                "errors": result.errors,
            }
            log.info(f"[ShelfBridge] {svc_id}: exported {result.records_exported} "
                     f"books -> {result.destination}")
        except Exception as e:
            log.error(f"[ShelfBridge] {svc_id} failed: {e}")
            summary["results"][svc_id] = {"success": False, "errors": [str(e)]}

    prefs["_last_export_summary"] = _scrub_summary(summary)
    return summary
