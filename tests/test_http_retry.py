"""Tests for the shared retry/backoff HTTP helper (adapters/http.py).

Policy under test: honor Retry-After on 429, exponential backoff on transient
5xx / network errors, no retry on other 4xx, give up after max_retries. ``sleep``
is injected so the suite never actually waits.
"""
import urllib.error
from email.message import Message

import pytest


def _http_error(code, retry_after=None):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError("http://x", code, "err", headers, None)


def _flaky(failures):
    """Return a thunk that raises each error in ``failures`` then returns 'ok'."""
    state = {"i": 0}

    def thunk():
        if state["i"] < len(failures):
            err = failures[state["i"]]
            state["i"] += 1
            raise err
        return "ok"

    return thunk


def test_retries_on_429_then_succeeds():
    from calibre_plugins.shelf_bridge.adapters.http import request_with_retry
    slept = []
    result = request_with_retry(
        _flaky([_http_error(429), _http_error(429)]), sleep=slept.append
    )
    assert result == "ok"
    assert len(slept) == 2


def test_honors_retry_after_header():
    from calibre_plugins.shelf_bridge.adapters.http import request_with_retry
    slept = []
    request_with_retry(
        _flaky([_http_error(429, retry_after="7")]), sleep=slept.append
    )
    assert slept == [7.0]


def test_no_retry_on_400():
    from calibre_plugins.shelf_bridge.adapters.http import request_with_retry
    slept = []
    with pytest.raises(urllib.error.HTTPError) as exc:
        request_with_retry(_flaky([_http_error(400)]), sleep=slept.append)
    assert exc.value.code == 400
    assert slept == []  # client error is not retryable


def test_gives_up_after_max_retries():
    from calibre_plugins.shelf_bridge.adapters.http import request_with_retry
    slept = []
    always_503 = _flaky([_http_error(503)] * 10)
    with pytest.raises(urllib.error.HTTPError) as exc:
        request_with_retry(always_503, max_retries=3, sleep=slept.append)
    assert exc.value.code == 503
    assert len(slept) == 3  # 3 retries, then the 4th attempt re-raises


def test_retries_on_network_error():
    from calibre_plugins.shelf_bridge.adapters.http import request_with_retry
    slept = []
    result = request_with_retry(
        _flaky([urllib.error.URLError("timeout")]), sleep=slept.append
    )
    assert result == "ok"
    assert len(slept) == 1


def test_exponential_backoff_without_retry_after():
    from calibre_plugins.shelf_bridge.adapters.http import request_with_retry
    slept = []
    request_with_retry(
        _flaky([_http_error(503), _http_error(503), _http_error(503)]),
        base_delay=0.5,
        sleep=slept.append,
    )
    assert slept == [0.5, 1.0, 2.0]  # 0.5 * 2**attempt
