"""Notion database adapter.

Re-exports upsert by Calibre ID: each book stores its ``calibre_id`` in a
"Calibre ID" number property; on export we query the database for an existing
page with that ID and PATCH it, otherwise create a new page. This keeps repeated
/ scheduled exports idempotent instead of duplicating the whole library.
(review I4)

All HTTP goes through :meth:`_request`, the single network seam (tests stub it).
"""
import json
import urllib.request
import urllib.parse
import urllib.error

from calibre_plugins.shelf_bridge.adapters.base import BaseServiceAdapter, ExportResult
from calibre_plugins.shelf_bridge.adapters.csv_schema import strip_html

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
CALIBRE_ID_PROP = "Calibre ID"


class NotionAdapter(BaseServiceAdapter):
    service_id = "notion"
    display_name = "Notion Database"
    requires_auth = True

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.prefs.get('notion_token', '')}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    def _request(self, method, url, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
        with urllib.request.urlopen(req) as r:
            body = r.read()
        return json.loads(body) if body else {}

    def _find_page_id(self, db_id, calibre_id):
        """Return the page id for an existing book, or None."""
        query = {
            "filter": {"property": CALIBRE_ID_PROP, "number": {"equals": calibre_id}},
            "page_size": 1,
        }
        try:
            resp = self._request("POST", f"{NOTION_API}/databases/{db_id}/query", query)
        except urllib.error.HTTPError:
            # Property may not exist yet on first run; treat as "no match".
            return None
        results = resp.get("results") or []
        return results[0]["id"] if results else None

    def export(self, books, field_map):
        db_id = self.prefs.get("notion_database_id", "")
        errors = []
        count = 0
        for b in books:
            props = self._build_properties(b)
            try:
                page_id = self._find_page_id(db_id, b["calibre_id"])
                if page_id:
                    self._request("PATCH", f"{NOTION_API}/pages/{page_id}",
                                  {"properties": props})
                else:
                    self._request("POST", f"{NOTION_API}/pages",
                                  {"parent": {"database_id": db_id}, "properties": props})
                count += 1
            except urllib.error.HTTPError as e:
                detail = e.read().decode() if hasattr(e, "read") else str(e)
                errors.append(f"{b.get('title', '?')}: {detail}")
            except Exception as e:
                errors.append(f"{b.get('title', '?')}: {e}")

        return ExportResult(
            success=len(errors) == 0,
            records_exported=count,
            destination=f"Notion DB {db_id}",
            errors=errors,
        )

    def _build_properties(self, b):
        rating = round((b.get("rating") or 0) / 2)
        props = {
            "Title":     {"title": [{"text": {"content": b.get("title", "")}}]},
            "Author":    {"rich_text": [{"text": {"content": "; ".join(b.get("authors", []))}}]},
            "ISBN":      {"rich_text": [{"text": {"content": b.get("isbn13") or b.get("isbn") or ""}}]},
            "Tags":      {"multi_select": [{"name": t} for t in b.get("tags", [])]},
            "Publisher": {"rich_text": [{"text": {"content": b.get("publisher") or ""}}]},
            "Review":    {"rich_text": [{"text": {"content": strip_html(b.get("comments"))[:1900]}}]},
            CALIBRE_ID_PROP: {"number": b["calibre_id"]},
        }
        # Notion rejects {"number": None}; only include rating when rated. (review 13)
        if rating:
            props["Rating"] = {"number": rating}
        return props

    def validate_prefs(self):
        errors = []
        if not self.prefs.get("notion_token"):
            errors.append("Notion integration token is required.")
        if not self.prefs.get("notion_database_id"):
            errors.append("Notion database ID is required.")
        return errors

    def test_connection(self):
        try:
            info = self._request("GET", f"{NOTION_API}/users/me")
            name = info.get("name") or info.get("bot", {}).get("owner", {}).get("type", "Notion")
            return True, f"Connected to Notion ({name})."
        except Exception as e:
            return False, str(e)
