"""Microsoft Graph token acquisition & refresh (OAuth2 device-code flow).

Security hardening vs. the original sketch:
- Explicit TLS context for every request (review C-2).
- ``poll_for_token`` has a deadline and a cooperative stop event, and handles
  ``slow_down`` / ``expired_token`` / transient network errors (review C-3, I-6, M-5).
- Tokens are persisted through :mod:`auth.credential_store` (OS keychain), not
  written into the plain prefs file (review C-1, arch C1).
- ``get_valid_token`` raises :class:`AuthExpiredError` on refresh failure so the
  UI can prompt a re-authorize instead of surfacing a raw traceback.
"""
import json
import ssl
import time
import threading
import urllib.request
import urllib.parse
import urllib.error

from calibre_plugins.shelf_bridge.auth import credential_store

TENANT = "common"
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token"
DEVICE_URL = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/devicecode"
SCOPES = "Files.ReadWrite offline_access"


class AuthExpiredError(Exception):
    """OneDrive authorization is missing or could not be refreshed."""


def _ssl_context():
    ctx = ssl.create_default_context()
    try:  # prefer vendored certifi if present
        import certifi
        ctx.load_verify_locations(cafile=certifi.where())
    except Exception:
        pass
    return ctx


def _post(url, fields):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, context=_ssl_context()) as r:
        return json.loads(r.read())


def start_device_flow(client_id):
    """Return the device-code response (user_code, verification_uri, interval...)."""
    return _post(DEVICE_URL, {"client_id": client_id, "scope": SCOPES})


def poll_for_token(client_id, device_code, interval=5, timeout_secs=900, stop_event=None):
    """Poll until the user completes auth, the deadline passes, or stop is set.

    Returns the token dict (with ``expires_at`` added). Raises on failure /
    timeout. ``stop_event`` lets the hosting QThread cancel cleanly.
    """
    deadline = time.time() + timeout_secs
    while time.time() < deadline:
        if stop_event is not None and stop_event.is_set():
            raise AuthExpiredError("Device authorization cancelled.")
        # Sleep in short slices so a stop_event is honoured promptly.
        slept = 0.0
        while slept < interval:
            if stop_event is not None and stop_event.is_set():
                raise AuthExpiredError("Device authorization cancelled.")
            time.sleep(min(0.5, interval - slept))
            slept += 0.5
        try:
            token = _post(TOKEN_URL, {
                "client_id": client_id,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
            })
            if "access_token" in token:
                token["expires_at"] = time.time() + token.get("expires_in", 3600)
                return token
        except urllib.error.HTTPError as e:
            body = {}
            try:
                body = json.loads(e.read())
            except Exception:
                pass
            err = body.get("error", "")
            if err == "authorization_pending":
                continue
            if err == "slow_down":
                interval = min(interval * 2, 30)
                continue
            if err in ("expired_token", "authorization_declined", "bad_verification_code", "access_denied"):
                raise AuthExpiredError(f"Device authorization failed: {err}")
            raise
        except urllib.error.URLError:
            continue  # transient network issue; keep trying until the deadline
    raise AuthExpiredError("Device code authorization timed out.")


def refresh_token(client_id, refresh_tok):
    token = _post(TOKEN_URL, {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_tok,
        "scope": SCOPES,
    })
    token["expires_at"] = time.time() + token.get("expires_in", 3600)
    return token


def save_token(token, prefs=None):
    """Persist the token blob to the OS credential store."""
    credential_store.set_secret("onedrive_token", token, prefs)


def get_valid_token(client_id, prefs=None):
    """Return a valid access-token string, refreshing if near expiry.

    Raises :class:`AuthExpiredError` if not authorized or refresh fails.
    """
    stored = credential_store.get_secret("onedrive_token", prefs)
    if not stored:
        raise AuthExpiredError("OneDrive is not authorized. Please authorize in Settings.")
    if time.time() > stored.get("expires_at", 0) - 60:
        try:
            stored = refresh_token(client_id, stored["refresh_token"])
        except Exception as e:
            credential_store.delete_secret("onedrive_token", prefs)
            raise AuthExpiredError(f"OneDrive token refresh failed: {e}") from e
        if "access_token" not in stored:
            credential_store.delete_secret("onedrive_token", prefs)
            raise AuthExpiredError("OneDrive refresh response missing access_token.")
        save_token(stored, prefs)
    return stored["access_token"]
