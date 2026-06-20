"""Google Sheets adapter.

Writes the library to a Google Sheet via the Sheets API v4. Re-exports are
idempotent: the target sheet is cleared, then the header + all rows are written
fresh (so a scheduled export never appends duplicates).

Rows are built from the user-configured columns (``columns.resolve_columns`` /
``columns.build_rows``), so the sheet's columns/order/headers are configurable.
All HTTP goes through :meth:`_request` (the single seam tests stub) and is
wrapped in ``request_with_retry`` for 429/5xx backoff.
"""
import json
import ssl
import urllib.request
import urllib.parse
import urllib.error

from calibre_plugins.shelf_bridge.adapters.base import BaseServiceAdapter, ExportResult
from calibre_plugins.shelf_bridge.columns import resolve_columns, build_rows
from calibre_plugins.shelf_bridge.adapters.http import request_with_retry
from calibre_plugins.shelf_bridge.auth.google_token import get_valid_token, AuthExpiredError
from calibre_plugins.shelf_bridge import oauth_apps

SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"


def _ssl_context():
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(cafile=certifi.where())
    except Exception:
        pass
    return ctx


class GoogleSheetsAdapter(BaseServiceAdapter):
    service_id = "google_sheets"
    display_name = "Google Sheets"
    requires_auth = True

    def _sheet_name(self):
        return self.prefs.get("google_sheet_name", "Books") or "Books"

    def _client_id(self):
        return oauth_apps.google_client_id(self.prefs.get("google_client_id", ""))

    def _client_secret(self):
        return oauth_apps.google_client_secret(self.prefs.get("google_client_secret", ""))

    def _request(self, method, url, token, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        def do():
            with urllib.request.urlopen(req, context=_ssl_context()) as r:
                body = r.read()
            return json.loads(body) if body else {}
        return request_with_retry(do)

    def _rows(self, books):
        custom = (books[0].get("custom_columns") if books else None) or {}
        cols = resolve_columns(self.prefs, custom)
        return build_rows(books, cols)

    def export(self, books, field_map):
        sheet_id = self.prefs.get("google_spreadsheet_id", "")
        client_id = self._client_id()
        client_secret = self._client_secret()
        try:
            token = get_valid_token(client_id, client_secret, self.prefs)
        except AuthExpiredError as e:
            return ExportResult(False, 0, sheet_id, [str(e)])

        name = urllib.parse.quote(self._sheet_name())
        try:
            # Clear existing contents, then write header + rows fresh (idempotent).
            self._request("POST", f"{SHEETS_API}/{sheet_id}/values/{name}!A:Z:clear", token, {})
            self._request(
                "PUT",
                f"{SHEETS_API}/{sheet_id}/values/{name}!A1?valueInputOption=RAW",
                token,
                {"range": f"{self._sheet_name()}!A1", "majorDimension": "ROWS",
                 "values": self._rows(books)},
            )
        except urllib.error.HTTPError as e:
            detail = e.read().decode() if hasattr(e, "read") else str(e)
            return ExportResult(False, 0, sheet_id, [f"Google Sheets write failed: {detail}"])
        except Exception as e:
            return ExportResult(False, 0, sheet_id, [f"Google Sheets write failed: {e}"])

        return ExportResult(
            success=True,
            records_exported=len(books),
            destination=f"https://docs.google.com/spreadsheets/d/{sheet_id}",
            errors=[],
        )

    def validate_prefs(self):
        from calibre_plugins.shelf_bridge.auth import credential_store
        errors = []
        if not self._client_id():
            errors.append("Google Client ID is required.")
        if not self._client_secret():
            errors.append("Google Client Secret is required.")
        if not self.prefs.get("google_spreadsheet_id"):
            errors.append("Google Spreadsheet ID is required.")
        if not credential_store.get_secret("google_token", self.prefs):
            errors.append("Google Sheets is not authorized. Click 'Authorize' in settings.")
        return errors

    def test_connection(self):
        try:
            sheet_id = self.prefs.get("google_spreadsheet_id", "")
            token = get_valid_token(self._client_id(), self._client_secret(), self.prefs)
            info = self._request(
                "GET", f"{SHEETS_API}/{sheet_id}?fields=properties.title", token)
            title = info.get("properties", {}).get("title", "spreadsheet")
            return True, f"Connected to Google Sheet: {title}"
        except Exception as e:
            return False, str(e)
