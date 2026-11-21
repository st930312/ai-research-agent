"""Market session presentation context (Asia/Taipei).

This handles weekends and early trading sessions without pretending that a
delayed scheduled run is still pre-open. Weekday exchange holidays should be
supplied by an official exchange calendar in a future extension.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from collections.abc import Collection


@dataclass(frozen=True)
class MarketSessionContext:
    report_date: date
    report_mode: str
    is_weekend: bool
    is_tw_trading_day: bool
    calendar_verified: bool
    latest_expected_tw_session: date
    heading: str
    watch_heading: str
    editorial_lens: str


def session_context(now: datetime, closed_dates: Collection[date] | None = None) -> MarketSessionContext:
    """Choose a report lens; never mistake the early session for pre-open.

    Weekdays are *potential* TW trading days (not holiday-calendar confirmed).
    The latest expected session is only a target for quote freshness checks,
    not proof that that session has closed or that prices are available.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("session_context requires timezone-aware datetime")
    from zoneinfo import ZoneInfo
    local = now.astimezone(ZoneInfo("Asia/Taipei"))
    today = local.date()
    weekend = today.weekday() >= 5
    calendar_verified = closed_dates is not None
    closed = set(closed_dates or ())
    is_open_day = not weekend and today not in closed
    expected = today
    if not is_open_day or local.time() < time(13, 30):
        expected -= timedelta(days=1)
    while expected.weekday() >= 5 or expected in closed:
        expected -= timedelta(days=1)

    if not is_open_day:
        mode, title, watch, lens = (
            "weekend_review", "台股週末市場回顧",
            "下個交易日觀察", "回顧最近完成的交易日與隔夜海外新聞；不要說今天開盤")
    elif local.time() < time(9):
        mode, title, watch, lens = (
            "premarket", "台股開盤前情報",
            "今日開盤觀察", "延續盤前分析：最近交易日收盤、隔夜市場與今天的觀察重點")
    elif local.time() < time(10):
        mode, title, watch, lens = (
            "early_session", "台股開盤初期情報",
            "今日盤勢觀察", "延續盤前分析邏輯；目前已開盤，但不得把昨日收盤價當成即時盤勢")
    elif local.time() < time(13, 30):
        mode, title, watch, lens = (
            "intraday", "台股盤中觀察",
            "後續盤勢觀察", "以已確認的歷史資料為基礎，未取得盤中行情時不得推測即時走勢")
    else:
        mode, title, watch, lens = (
            "postmarket", "台股盤後觀察",
            "下個交易日觀察", "僅在已取得當日確認收盤行情時引用當日收盤數據")
    return MarketSessionContext(today, mode, weekend, is_open_day,
                                calendar_verified, expected, title, watch, lens)
