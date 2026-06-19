"""Optional bundled OAuth app credentials for one-click authorization.

When these are filled in, users do not need to register their own OAuth apps —
the adapters fall back to these defaults and the config dialog's credential
fields become optional. Left empty by default, which keeps the plugin in
"bring your own credentials" mode.

These are PUBLIC client identifiers, not confidential secrets:
- OneDrive uses a public client (no confidential secret at all).
- Google's device flow uses an installed-app client whose "secret" is not
  treated as confidential by Google (it is expected to ship inside the app).

Only fill these in once the apps are registered and — for Google's sensitive
``spreadsheets`` scope — verified for public distribution.
"""

ONEDRIVE_CLIENT_ID = ""
GOOGLE_CLIENT_ID = ""
GOOGLE_CLIENT_SECRET = ""


def _resolve(pref_value, default):
    """User-supplied value wins; otherwise the bundled default (if any)."""
    return (pref_value or "").strip() or default


def onedrive_client_id(pref_value):
    return _resolve(pref_value, ONEDRIVE_CLIENT_ID)


def google_client_id(pref_value):
    return _resolve(pref_value, GOOGLE_CLIENT_ID)


def google_client_secret(pref_value):
    return _resolve(pref_value, GOOGLE_CLIENT_SECRET)


def has_bundled_onedrive():
    return bool(ONEDRIVE_CLIENT_ID)


def has_bundled_google():
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
