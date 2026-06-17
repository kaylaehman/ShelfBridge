"""Shared HTTP retry/backoff helper for the API adapters.

All adapters that hit a rate-limited API (Hardcover, OneDrive) route their
requests through :func:`request_with_retry` so the policy lives in one place.
Policy:

* **429 Too Many Requests** — honor the server's ``Retry-After`` header when it
  is a numeric seconds value; otherwise fall back to exponential backoff.
* **5xx / network errors** (timeouts, connection resets) — exponential backoff.
* **Other 4xx** — not retried; the error propagates immediately.
* After ``max_retries`` retries the last error is re-raised so the caller can
  record it in ``ExportResult.errors``.

``sleep`` is injectable so tests run without waiting.
"""
import time
import urllib.error

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_DELAY = 0.5


def _backoff_seconds(err, attempt, base_delay):
    """Seconds to wait before the next attempt.

    On a 429 with a numeric ``Retry-After`` header, honor it exactly. Otherwise
    (5xx, network error, or a non-numeric HTTP-date Retry-After) use exponential
    backoff: base_delay * 2**attempt.
    """
    headers = getattr(err, "headers", None)
    if headers is not None:
        retry_after = headers.get("Retry-After")
        if retry_after:
            try:
                return float(retry_after)
            except (TypeError, ValueError):
                pass  # HTTP-date form — fall through to exponential backoff
    return base_delay * (2 ** attempt)


def request_with_retry(do_request, max_retries=DEFAULT_MAX_RETRIES,
                       base_delay=DEFAULT_BASE_DELAY, sleep=time.sleep):
    """Call ``do_request`` (a zero-arg thunk), retrying transient failures.

    Returns whatever ``do_request`` returns. Re-raises the last exception once
    retries are exhausted or the error is not retryable.
    """
    attempt = 0
    while True:
        try:
            return do_request()
        except urllib.error.HTTPError as e:
            if e.code not in RETRYABLE_STATUS or attempt >= max_retries:
                raise
            sleep(_backoff_seconds(e, attempt, base_delay))
        except urllib.error.URLError:
            if attempt >= max_retries:
                raise
            sleep(base_delay * (2 ** attempt))
        attempt += 1
