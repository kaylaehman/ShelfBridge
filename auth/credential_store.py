"""Secure credential storage backed by the OS keychain.

The plugin's ``JSONConfig`` prefs file is plain text on disk, so API tokens and
OAuth blobs must NOT live there. This module stores them in the operating
system's credential store via the vendored ``keyring`` package (Windows
Credential Manager / macOS Keychain / Secret Service on Linux).

If ``keyring`` is unavailable or its backend is non-functional, it falls back to
the prefs file and logs a prominent warning — functionality is preserved, but
the user is told their tokens are not encrypted.

Adapters never call this directly. The runtime calls :func:`with_secrets` when
constructing an adapter so the adapter sees the resolved secret under the same
pref key it already expects (e.g. ``self.prefs["notion_token"]``).
"""
import json

try:
    from calibre.utils.logging import default_log as log
except Exception:  # pragma: no cover - outside Calibre (tests)
    class _Log:
        def info(self, *a, **k):
            pass
        warn = warning = error = debug = info
    log = _Log()

_SERVICE = "calibre-shelf-bridge"

# Keys whose values are secrets and must be kept out of the plain prefs file.
SECRET_KEYS = frozenset({
    "notion_token",
    "airtable_token",
    "hardcover_token",
    "onedrive_token",   # dict blob -> JSON-encoded in the keychain
})

# Secrets that are stored as a JSON-encoded structure rather than a bare string.
_JSON_KEYS = frozenset({"onedrive_token"})

_keyring = None
_keyring_ok = None  # tri-state: None=unknown, True/False=probed


def _backend():
    """Return a working ``keyring`` module, or None if unavailable.

    Probes once and caches the result. A keyring with the "fail" backend (no
    real secure store) is treated as unavailable so we fall back rather than
    silently losing secrets.
    """
    global _keyring, _keyring_ok
    if _keyring_ok is not None:
        return _keyring if _keyring_ok else None
    try:
        import keyring
        from keyring.backends.fail import Keyring as FailKeyring
        backend = keyring.get_keyring()
        if isinstance(backend, FailKeyring):
            raise RuntimeError("no functional keyring backend")
        _keyring = keyring
        _keyring_ok = True
        log.info("[ShelfBridge] Using OS keyring backend: %s" % backend.__class__.__name__)
    except Exception as e:
        _keyring = None
        _keyring_ok = False
        log.warn(
            "[ShelfBridge] OS keyring unavailable (%s). Tokens will be stored in "
            "the plain-text preferences file. Install a keyring backend for "
            "secure storage." % e
        )
    return _keyring


def _encode(key, value):
    return json.dumps(value) if key in _JSON_KEYS else str(value)


def _decode(key, raw):
    if raw is None:
        return None
    if key in _JSON_KEYS:
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return None
    return raw


def get_secret(key, prefs=None):
    """Return the stored secret for ``key`` (keyring first, then prefs fallback).

    ``prefs`` is consulted only when no keyring backend is available.
    Returns ``""`` (or ``{}`` for JSON keys) when nothing is stored.
    """
    empty = {} if key in _JSON_KEYS else ""
    kr = _backend()
    if kr is not None:
        try:
            raw = kr.get_password(_SERVICE, key)
            decoded = _decode(key, raw)
            if decoded is not None:
                return decoded
            return empty
        except Exception as e:  # pragma: no cover - backend hiccup
            log.warn("[ShelfBridge] keyring read failed for %r: %s" % (key, e))
    if prefs is not None:
        return prefs.get(key, empty)
    return empty


def set_secret(key, value, prefs=None):
    """Persist a secret. Uses keyring when available, else the prefs fallback."""
    kr = _backend()
    if kr is not None:
        try:
            if value in (None, "", {}):
                delete_secret(key, prefs)
            else:
                kr.set_password(_SERVICE, key, _encode(key, value))
            return
        except Exception as e:  # pragma: no cover
            log.warn("[ShelfBridge] keyring write failed for %r: %s" % (key, e))
    if prefs is not None:
        prefs[key] = value


def delete_secret(key, prefs=None):
    kr = _backend()
    if kr is not None:
        try:
            kr.delete_password(_SERVICE, key)
        except Exception:
            pass
    if prefs is not None and key in prefs:
        try:
            del prefs[key]
        except Exception:
            pass


def with_secrets(prefs):
    """Return a plain dict view of ``prefs`` with secret keys resolved.

    Adapters receive this so they can read ``self.prefs["notion_token"]`` exactly
    as the spec describes while the actual storage is the OS keychain. Falls back
    to whatever is already in ``prefs`` for keys with no stored secret.
    """
    merged = dict(prefs)
    for key in SECRET_KEYS:
        secret = get_secret(key, prefs)
        if secret not in (None, "", {}):
            merged[key] = secret
    return merged
