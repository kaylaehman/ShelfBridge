"""Wiring tests: each API adapter routes its network seam through
``request_with_retry`` so a transient 429 is retried rather than failing the book.

The retry *logic* is covered in test_http_retry.py; these tests prove each
adapter is actually wired to it. ``request_with_retry`` is swapped for a variant
with an instant sleep so the suite never waits.
"""
import urllib.error
from email.message import Message

from calibre_plugins.shelf_bridge.adapters import http


def _http_error(code, retry_after=None):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError("http://x", code, "err", headers, None)


class _FakeResp:
    def __init__(self, body=b"{}"):
        self._body = body
        self.status = 200

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _instant_retry(monkeypatch, module):
    """Make the module's request_with_retry sleep instantly."""
    monkeypatch.setattr(
        module, "request_with_retry",
        lambda fn, **kw: http.request_with_retry(fn, sleep=lambda _s: None, **kw),
    )


def _flaky_urlopen(calls, body=b"{}"):
    """urlopen that raises 429 on the first call, then returns a fake response."""
    def fake(req, *a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _http_error(429)
        return _FakeResp(body)
    return fake


def test_hardcover_gql_retries_on_429(monkeypatch):
    import calibre_plugins.shelf_bridge.adapters.hardcover as mod
    _instant_retry(monkeypatch, mod)
    calls = {"n": 0}
    monkeypatch.setattr(mod.urllib.request, "urlopen",
                        _flaky_urlopen(calls, body=b'{"data": {}}'))
    adapter = mod.HardcoverAdapter({"hardcover_token": "t"})
    assert adapter._gql("query {}", {}) == {"data": {}}
    assert calls["n"] == 2


def test_onedrive_upload_retries_on_429(monkeypatch):
    import calibre_plugins.shelf_bridge.adapters.onedrive as mod
    _instant_retry(monkeypatch, mod)
    calls = {"n": 0}
    monkeypatch.setattr(mod.urllib.request, "urlopen",
                        _flaky_urlopen(calls, body=b'{"webUrl": "https://od/x.csv"}'))
    adapter = mod.OneDriveAdapter({})
    assert adapter._simple_upload(b"data", "Calibre/x.csv", "tok") == "https://od/x.csv"
    assert calls["n"] == 2
