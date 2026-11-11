"""Bounded exponential backoff for transient remote-source failures only.

Avoid retrying invalid URLs, permanent 4xx responses, parsing failures or
source-integrity errors. The request callable is invoked at most 3 times.
"""
from __future__ import annotations

import email.utils
import random
import time
import urllib.error
from datetime import datetime, timezone

TRANSIENT_HTTP = frozenset((408, 429, 500, 502, 503, 504))


def _retry_after(error):
    headers = getattr(error, "headers", None)
    if headers is None:
        return None
    value = headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        try:
            date = email.utils.parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            return max(0.0, (date - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


def backoff_delay(attempt, error=None, base=3.0, cap=30.0):
    """Attempt is 1-based: 3-6 s, 6-12 s, capped at 30 s."""
    exponential = min(cap, base * (2 ** (attempt - 1)))
    delay = random.uniform(exponential, min(cap, exponential * 2))
    if isinstance(error, urllib.error.HTTPError):
        requested = _retry_after(error)
        if requested is not None:
            delay = max(delay, requested)
    return min(cap, delay)


def transient_error(error):
    if isinstance(error, urllib.error.HTTPError):
        return error.code in TRANSIENT_HTTP
    return isinstance(error, (urllib.error.URLError, TimeoutError, ConnectionError))


def with_backoff(action, *, retries=2, label="remote"):
    """Retries only known transient failures; never retries other exceptions."""
    for attempt in range(retries + 1):
        try:
            return action()
        except Exception as exc:
            if attempt == retries or not transient_error(exc):
                raise
            delay = backoff_delay(attempt + 1, exc)
            print(f"RETRY_TRANSIENT source={label} attempt={attempt + 1}/{retries} "
                  f"error={type(exc).__name__} sleep_s={delay:.1f}", flush=True)
            time.sleep(delay)
