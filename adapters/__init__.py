"""Adapter registry.

``get_adapter(service_id, prefs)`` constructs an adapter whose prefs have secret
keys resolved from the OS credential store (so adapters can read
``self.prefs["notion_token"]``-style keys while storage stays in the keychain).
``list_adapters()`` returns the adapter classes for UI enumeration.
"""
from calibre_plugins.shelf_bridge.adapters.goodreads import GoodreadsAdapter
from calibre_plugins.shelf_bridge.adapters.storygraph import StoryGraphAdapter
from calibre_plugins.shelf_bridge.adapters.onedrive import OneDriveAdapter
from calibre_plugins.shelf_bridge.adapters.google_sheets import GoogleSheetsAdapter

_ADAPTERS = [
    GoodreadsAdapter, StoryGraphAdapter, OneDriveAdapter, GoogleSheetsAdapter,
]
_BY_ID = {a.service_id: a for a in _ADAPTERS}


def get_adapter(service_id, prefs):
    try:
        cls = _BY_ID[service_id]
    except KeyError:
        raise ValueError(f"Unknown service_id: {service_id!r}")
    from calibre_plugins.shelf_bridge.auth import credential_store
    return cls(credential_store.with_secrets(prefs))


def list_adapters():
    """Return adapter classes (each has .service_id / .display_name attrs)."""
    return list(_ADAPTERS)
