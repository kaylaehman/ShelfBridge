"""Hardcover adapter (GraphQL).

Adds books by ISBN to the user's library with a read/want-to-read status.
``add_book_by_isbn`` is idempotent at the API level, so no local dedup is needed.
"""
import json
import urllib.request
import urllib.error

from calibre_plugins.shelf_bridge.adapters.base import BaseServiceAdapter, ExportResult

HARDCOVER_API = "https://api.hardcover.app/v1/graphql"

ADD_BOOK = """
mutation AddBook($isbn: String!, $status: UserBookStatusEnum!) {
  add_book_by_isbn(isbn: $isbn, status: $status) { id }
}
"""


class HardcoverAdapter(BaseServiceAdapter):
    service_id = "hardcover"
    display_name = "Hardcover"
    requires_auth = True

    def _gql(self, query, variables):
        payload = json.dumps({"query": query, "variables": variables}).encode()
        req = urllib.request.Request(
            HARDCOVER_API,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.prefs.get('hardcover_token', '')}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req) as r:
            resp = json.loads(r.read())
        if resp.get("errors"):
            raise RuntimeError(resp["errors"])
        return resp

    def export(self, books, field_map):
        errors = []
        count = 0
        for b in books:
            isbn = b.get("isbn13") or b.get("isbn")
            if not isbn:
                errors.append(f"'{b.get('title', '?')}' skipped — no ISBN.")
                continue
            status = "read" if (b.get("rating") or b.get("read_dates")) else "want_to_read"
            try:
                self._gql(ADD_BOOK, {"isbn": isbn, "status": status})
                count += 1
            except Exception as e:
                errors.append(f"'{b.get('title', '?')}': {e}")

        return ExportResult(
            success=count > 0 and not errors,
            records_exported=count,
            destination="Hardcover library",
            errors=errors,
        )

    def validate_prefs(self):
        errors = []
        if not self.prefs.get("hardcover_token"):
            errors.append("Hardcover API token is required.")
        return errors

    def test_connection(self):
        try:
            self._gql("query { me { username } }", {})
            return True, "Connected to Hardcover."
        except Exception as e:
            return False, str(e)
