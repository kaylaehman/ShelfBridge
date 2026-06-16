"""Goodreads / StoryGraph CSV adapter.

Produces a local CSV file in the Goodreads import schema (StoryGraph accepts the
same format). Always UTF-8 with BOM so Excel opens it correctly on Windows.
"""
import csv
import os

from calibre_plugins.shelf_bridge.adapters.base import BaseServiceAdapter, ExportResult
from calibre_plugins.shelf_bridge.adapters.csv_schema import (
    GOODREADS_COLUMNS, goodreads_row,
)


class GoodreadsAdapter(BaseServiceAdapter):
    service_id = "goodreads"
    display_name = "Goodreads / StoryGraph CSV"
    requires_auth = False

    # The prefs key holding this adapter's output path. StoryGraph overrides it
    # so the two services never clobber each other's file. (review M5)
    path_pref = "goodreads_output_path"

    COLUMNS = GOODREADS_COLUMNS

    def _output_path(self):
        return self.prefs.get(self.path_pref, "")

    def export(self, books, field_map):
        output_path = self._output_path()
        rows = [goodreads_row(b) for b in books]
        try:
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=GOODREADS_COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
        except OSError as e:
            # Contract: export never raises for expected failures. (review M6)
            return ExportResult(
                success=False,
                records_exported=0,
                destination=output_path,
                errors=[f"Could not write CSV to {output_path!r}: {e}"],
            )
        return ExportResult(
            success=True,
            records_exported=len(rows),
            destination=output_path,
            errors=[],
        )

    def validate_prefs(self):
        errors = []
        path = self._output_path()
        if not path:
            errors.append(f"{self.display_name}: output path is required.")
            return errors
        if not path.lower().endswith(".csv"):
            errors.append(f"{self.display_name}: output path must end in .csv.")
        parent = os.path.dirname(os.path.abspath(path))
        if not os.path.isdir(parent):
            errors.append(f"{self.display_name}: output directory does not exist: {parent}")
        return errors
