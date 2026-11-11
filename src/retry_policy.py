"""Bounded backoff for transient remote-source and NVIDIA API failures.

Retries are per operation, not per workflow. Permanent errors are not retried.
"""
from __future__ import annotations

import email.utils
import random
import time
import urllib.error
from datetime import datetime, timezone

TRANSIENT_HTTP = frozenset((408, 429, 500, 502, 503, 504))
MAX_RETRIES = 3
RATE_LIMIT_SECONDS = (60, 90, 120)
NETWORK_SECONDS = (15, 30, 60)
AI_CONTENT_SECONDS = (20, 40, 60)
JITTER_SECONDS = 3


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


def _jittered(seconds):
    return seconds + random.uniform(0, JITTER_SECONDS)


def backoff_delay(attempt, error=None):
    """1-based attempt: 429 -> 60/90/120s; network/5xx -> 15/30/60s.

    Retry-After is a *minimum* and is never capped below the provider value.
    """
    if not 1 <= attempt <= MAX_RETRIES:
        raise ValueError("Retry attempt out of range")
    rate_limited = isinstance(error, urllib.error.HTTPError) and error.code == 429
    seconds = (RATE_LIMIT_SECONDS if rate_limited else NETWORK_SECONDS)[attempt - 1]
    delay = _jittered(seconds)
    if isinstance(error, urllib.error.HTTPError):
        requested = _retry_after(error)
        if requested is not None:
            delay = max(delay, requested)
    return delay


def ai_content_delay(attempt):
    """Missing/invalid AI content: 20/40/60 seconds plus bounded jitter."""
    if not 1 <= attempt <= MAX_RETRIES:
        raise ValueError("Retry attempt out of range")
    return _jittered(AI_CONTENT_SECONDS[attempt - 1])


def transient_error(error):
    if isinstance(error, urllib.error.HTTPError):
        return error.code in TRANSIENT_HTTP
    return isinstance(error, (urllib.error.URLError, TimeoutError, ConnectionError))


def with_backoff(action, *, retries=MAX_RETRIES, label="remote"):
    """Retry only known transient failures; at most three retries by default."""
    if not 0 <= retries <= MAX_RETRIES:
        raise ValueError("Invalid retry count")
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
