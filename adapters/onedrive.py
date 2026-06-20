"""OneDrive adapter — uploads the CSV via Microsoft Graph.

OneDrive is a transport, not a schema: it builds the CSV from the user-configured
columns (``columns.resolve_columns`` / ``columns.build_rows``) and uploads it with
a simple PUT (<4 MB) or a resumable upload session (>=4 MB).
"""
import csv
import io
import json
import re
import ssl
import urllib.request
import urllib.parse
import urllib.error

from calibre_plugins.shelf_bridge.adapters.base import BaseServiceAdapter, ExportResult
from calibre_plugins.shelf_bridge.columns import resolve_columns, build_rows
from calibre_plugins.shelf_bridge.adapters.http import request_with_retry
from calibre_plugins.shelf_bridge.auth.graph_token import get_valid_token, AuthExpiredError
from calibre_plugins.shelf_bridge import oauth_apps

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_SAFE_PATH = re.compile(r"^[\w/.\- ]+\.csv$")


def _ssl_context():
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(cafile=certifi.where())
    except Exception:
        pass
    return ctx


def _open(req):
    return request_with_retry(lambda: urllib.request.urlopen(req, context=_ssl_context()))


class OneDriveAdapter(BaseServiceAdapter):
    service_id = "onedrive"
    display_name = "OneDrive (CSV)"
    requires_auth = True

    def _client_id(self):
        # User's own client ID wins; otherwise the bundled shared app (if any).
        return oauth_apps.onedrive_client_id(self.prefs.get("onedrive_client_id", ""))

    def _remote_path(self):
        return self.prefs.get("onedrive_path", "/Calibre/catalog.csv").lstrip("/")

    def _build_csv_bytes(self, books):
        custom = (books[0].get("custom_columns") if books else None) or {}
        rows = build_rows(books, resolve_columns(self.prefs, custom))
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerows(rows)
        return buf.getvalue().encode("utf-8-sig")

    def export(self, books, field_map):
        client_id = self._client_id()
        remote_path = self._remote_path()
        try:
            access_token = get_valid_token(client_id, self.prefs)
        except AuthExpiredError as e:
            return ExportResult(False, 0, remote_path, [str(e)])

        csv_bytes = self._build_csv_bytes(books)
        try:
            if len(csv_bytes) < 4 * 1024 * 1024:
                web_url = self._simple_upload(csv_bytes, remote_path, access_token)
            else:
                web_url = self._upload_large(csv_bytes, remote_path, access_token)
        except urllib.error.HTTPError as e:
            detail = e.read().decode() if hasattr(e, "read") else str(e)
            return ExportResult(False, 0, remote_path, [f"OneDrive upload failed: {detail}"])
        except Exception as e:
            return ExportResult(False, 0, remote_path, [f"OneDrive upload failed: {e}"])

        return ExportResult(
            success=True,
            records_exported=len(books),
            destination=web_url,
            errors=[],
        )

    def _simple_upload(self, data, remote_path, token):
        url = f"{GRAPH_BASE}/me/drive/root:/{urllib.parse.quote(remote_path)}:/content"
        req = urllib.request.Request(
            url, data=data, method="PUT",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "text/csv"},
        )
        with _open(req) as r:
            resp = json.loads(r.read())
        return resp.get("webUrl", remote_path)

    def _upload_large(self, data, remote_path, token):
        session_url = f"{GRAPH_BASE}/me/drive/root:/{urllib.parse.quote(remote_path)}:/createUploadSession"
        req = urllib.request.Request(
            session_url,
            data=json.dumps({"item": {"@microsoft.graph.conflictBehavior": "replace"}}).encode(),
            method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        with _open(req) as r:
            upload_url = json.loads(r.read())["uploadUrl"]
        if not upload_url.startswith("https://"):
            raise ValueError("Upload session returned a non-HTTPS URL.")

        chunk_size = 5 * 1024 * 1024
        offset = 0
        total = len(data)
        final_resp = {}
        while offset < total:
            chunk = data[offset:offset + chunk_size]
            end = offset + len(chunk) - 1
            put = urllib.request.Request(
                upload_url, data=chunk, method="PUT",
                headers={
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {offset}-{end}/{total}",
                },
            )
            with _open(put) as r:
                # 202 = chunk accepted, more to come; 200/201 = complete. (review I7)
                if r.status in (200, 201):
                    final_resp = json.loads(r.read())
            offset += chunk_size
        return final_resp.get("webUrl", remote_path)

    def validate_prefs(self):
        from calibre_plugins.shelf_bridge.auth import credential_store
        errors = []
        if not self._client_id():
            errors.append("OneDrive Client ID is required.")
        if not credential_store.get_secret("onedrive_token", self.prefs):
            errors.append("OneDrive is not authorized. Click 'Authorize' in settings.")
        path = self.prefs.get("onedrive_path", "")
        if path:
            if not path.lower().endswith(".csv"):
                errors.append("OneDrive path must end in .csv (e.g. /Calibre/catalog.csv).")
            cleaned = path.lstrip("/")
            if ".." in cleaned.split("/") or not _SAFE_PATH.match(cleaned):
                errors.append("OneDrive path contains invalid characters or traversal.")
        return errors

    def test_connection(self):
        try:
            client_id = self._client_id()
            token = get_valid_token(client_id, self.prefs)
            req = urllib.request.Request(
                f"{GRAPH_BASE}/me/drive",
                headers={"Authorization": f"Bearer {token}"},
            )
            with _open(req) as r:
                info = json.loads(r.read())
            name = info.get("owner", {}).get("user", {}).get("displayName", "unknown")
            return True, f"Connected as {name}"
        except Exception as e:
            return False, str(e)
