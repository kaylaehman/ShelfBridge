"""Base service adapter interface.

All adapters implement this interface. Service-specific logic lives in the
adapter, never in ``main.py`` or ``books.py``. Adapters consume BookDict dicts
and return an :class:`ExportResult`; ``export`` should not raise for expected
failures — catch them and report via ``ExportResult.errors``.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExportResult:
    success: bool
    records_exported: int
    destination: str          # human-readable: filepath, URL, database name
    errors: list              # list[str]
    raw_response: Any = None


class BaseServiceAdapter(ABC):
    # Set in each subclass
    service_id: str = ""        # machine key: "goodreads", "onedrive", etc.
    display_name: str = ""      # shown in UI
    requires_auth: bool = False
    supports_field_mapping: bool = True

    def __init__(self, prefs):
        self.prefs = prefs

    def validate_prefs(self):
        """Return list of error strings, empty = valid."""
        return []

    @abstractmethod
    def export(self, books, field_map):
        """Run the export. Returns an ExportResult."""
        ...

    def test_connection(self):
        """Quick connectivity check. Returns (ok, message)."""
        return True, "Not implemented"
