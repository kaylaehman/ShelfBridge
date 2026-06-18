"""Google OAuth2 token acquisition & refresh (device-code flow).

Mirrors ``graph_token`` for Microsoft, but for Google's device flow used by the
Google Sheets adapter. Google's device flow requires a Desktop-app
``client_id`` + ``client_secret`` (the secret is not truly confidential for
installed apps, but the token exchange demands it).

Security: explicit TLS context, a polling deadline + cooperative stop event,
``slow_down`` / ``expired`` handling, and token persistence through
``credential_store`` (OS keychain) rather than the plain prefs file.
"""
import json
import ssl
import time
import urllib.request
import urllib.parse
import urllib.error

from calibre_plugins.shelf_bridge.auth import credential_store

DEVICE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/spreadsheets"


class AuthExpiredError(Exception):
    """Google Sheets authorization is missing or could not be refreshed."""


def _ssl_context():
    ctx = ssl.create_default_context()
    try:
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
    """Return the device-code response (user_code, verification_url, interval...)."""
    return _post(DEVICE_URL, {"client_id": client_id, "scope": SCOPES})


def poll_for_token(client_id, client_secret, device_code, interval=5,
                   timeout_secs=900, stop_event=None):
    """Poll until the user completes auth, the deadline passes, or stop is set."""
    deadline = time.time() + timeout_secs
    while time.time() < deadline:
        if stop_event is not None and stop_event.is_set():
            raise AuthExpiredError("Device authorization cancelled.")
        slept = 0.0
        while slept < interval:
            if stop_event is not None and stop_event.is_set():
                raise AuthExpiredError("Device authorization cancelled.")
            time.sleep(min(0.5, interval - slept))
            slept += 0.5
        try:
            token = _post(TOKEN_URL, {
                "client_id": client_id,
                "client_secret": client_secret,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
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
            if err in ("expired_token", "access_denied"):
                raise AuthExpiredError(f"Device authorization failed: {err}")
            raise
        except urllib.error.URLError:
            continue
    raise AuthExpiredError("Device code authorization timed out.")


def refresh_token(client_id, client_secret, refresh_tok):
    token = _post(TOKEN_URL, {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_tok,
        "grant_type": "refresh_token",
    })
    token["expires_at"] = time.time() + token.get("expires_in", 3600)
    # Google omits refresh_token on refresh; carry the old one forward.
    token.setdefault("refresh_token", refresh_tok)
    return token


def save_token(token, prefs=None):
    credential_store.set_secret("google_token", token, prefs)


def get_valid_token(client_id, client_secret, prefs=None):
    """Return a valid access-token string, refreshing if near expiry.

    Raises :class:`AuthExpiredError` if not authorized or refresh fails.
    """
    stored = credential_store.get_secret("google_token", prefs)
    if not stored:
        raise AuthExpiredError("Google Sheets is not authorized. Please authorize in Settings.")
    if time.time() > stored.get("expires_at", 0) - 60:
        try:
            stored = refresh_token(client_id, client_secret, stored["refresh_token"])
        except Exception as e:
            credential_store.delete_secret("google_token", prefs)
            raise AuthExpiredError(f"Google token refresh failed: {e}") from e
        if "access_token" not in stored:
            credential_store.delete_secret("google_token", prefs)
            raise AuthExpiredError("Google refresh response missing access_token.")
        save_token(stored, prefs)
    return stored["access_token"]
