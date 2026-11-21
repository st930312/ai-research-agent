"""TWSE official annual holiday schedule; cached per Python process.

See https://www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule
A failed lookup never turns a weekday into a confirmed trading day.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import date
from functools import lru_cache

NOT_CLOSED_NAMES = ("最後交易日", "開始交易日")


def parse_twse_holidays(payload: dict, year: int) -> set[date]:
    if payload.get("stat") != "ok" or not isinstance(payload.get("data"), list):
        raise ValueError("TWSE holiday schedule unavailable")
    days = set()
    for row in payload["data"]:
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            continue
        when, name = row[0], str(row[1])
        if any(token in name for token in NOT_CLOSED_NAMES):
            continue
        try:
            day = date.fromisoformat(str(when))
        except ValueError:
            continue
        if day.year == year:
            days.add(day)
    if not days:
        raise ValueError("TWSE holiday schedule empty")
    return days


@lru_cache(maxsize=4)
def fetch_twse_holidays(year: int, fetcher=None) -> frozenset[date]:
    """Fail closed to unknown calendar, not fabricated holidays."""
    base = "https://www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule"
    url = base + "?" + urllib.parse.urlencode({
        "response": "json", "date": str(year),
    })
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; AIResearchAgent/1.0)",
        "Accept": "application/json",
    })
    opener = fetcher or urllib.request.urlopen
    with opener(request, timeout=8) as response:
        payload = json.loads(response.read(150000))
    return frozenset(parse_twse_holidays(payload, year))
