"""Airtable adapter.

Like Notion, re-exports upsert by Calibre ID: a "Calibre ID" field is matched
via ``filterByFormula``; existing records are PATCHed, new ones POSTed. (review I4)
The spec listed Airtable without code; this mirrors the Notion adapter's shape.

All HTTP goes through :meth:`_request` (the single network seam tests stub).
"""
import json
import urllib.request
import urllib.parse
import urllib.error

from calibre_plugins.shelf_bridge.adapters.base import BaseServiceAdapter, ExportResult
from calibre_plugins.shelf_bridge.adapters.csv_schema import strip_html

AIRTABLE_API = "https://api.airtable.com/v0"
CALIBRE_ID_FIELD = "Calibre ID"


class AirtableAdapter(BaseServiceAdapter):
    service_id = "airtable"
    display_name = "Airtable"
    requires_auth = True

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.prefs.get('airtable_token', '')}",
            "Content-Type": "application/json",
        }

    def _table_url(self):
        base_id = self.prefs.get("airtable_base_id", "")
        table = self.prefs.get("airtable_table_name", "Books")
        return f"{AIRTABLE_API}/{base_id}/{urllib.parse.quote(table)}"

    def _request(self, method, url, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
        with urllib.request.urlopen(req) as r:
            body = r.read()
        return json.loads(body) if body else {}

    def _find_record_id(self, calibre_id):
        formula = "{%s}=%d" % (CALIBRE_ID_FIELD, calibre_id)
        url = self._table_url() + "?" + urllib.parse.urlencode({
            "filterByFormula": formula, "maxRecords": 1,
        })
        try:
            resp = self._request("GET", url)
        except urllib.error.HTTPError:
            return None
        records = resp.get("records") or []
        return records[0]["id"] if records else None

    def export(self, books, field_map):
        errors = []
        count = 0
        for b in books:
            fields = self._fields(b)
            try:
                rec_id = self._find_record_id(b["calibre_id"])
                if rec_id:
                    self._request("PATCH", f"{self._table_url()}/{rec_id}", {"fields": fields})
                else:
                    self._request("POST", self._table_url(), {"fields": fields})
                count += 1
            except urllib.error.HTTPError as e:
                detail = e.read().decode() if hasattr(e, "read") else str(e)
                errors.append(f"{b.get('title', '?')}: {detail}")
            except Exception as e:
                errors.append(f"{b.get('title', '?')}: {e}")

        return ExportResult(
            success=len(errors) == 0,
            records_exported=count,
            destination=f"Airtable {self.prefs.get('airtable_base_id', '')}/"
                        f"{self.prefs.get('airtable_table_name', 'Books')}",
            errors=errors,
        )

    def _fields(self, b):
        rating = round((b.get("rating") or 0) / 2)
        fields = {
            CALIBRE_ID_FIELD: b["calibre_id"],
            "Title": b.get("title", ""),
            "Author": "; ".join(b.get("authors", [])),
            "ISBN": b.get("isbn13") or b.get("isbn") or "",
            "Tags": b.get("tags", []),
            "Publisher": b.get("publisher") or "",
            "Notes": strip_html(b.get("comments")),
        }
        if rating:
            fields["Rating"] = rating
        return fields

    def validate_prefs(self):
        errors = []
        if not self.prefs.get("airtable_token"):
            errors.append("Airtable Personal Access Token is required.")
        if not self.prefs.get("airtable_base_id"):
            errors.append("Airtable Base ID is required.")
        return errors

    def test_connection(self):
        try:
            url = self._table_url() + "?" + urllib.parse.urlencode({"maxRecords": 1})
            self._request("GET", url)
            return True, "Connected to Airtable."
        except Exception as e:
            return False, str(e)
