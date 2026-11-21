"""Unit tests for conservative stock evidence handling."""
import unittest
from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src.market_calendar import parse_twse_holidays
from src.market_session import session_context
from src.stock_safety import unsupported_indicator_issues, safe_redact_sections
from src.digest_services import StockService


TZ = ZoneInfo("Asia/Taipei")


class MarketCalendarTests(unittest.TestCase):
    def test_twse_excludes_last_and_first_trading_day(self):
        payload = {"stat": "ok", "data": [
            ["2026-02-11", "農曆春節前最後交易日", ""],
            ["2026-02-12", "市場無交易，僅辦理結算交割作業", ""],
            ["2026-02-13", "農曆除夕及春節", "休市"],
            ["2026-02-23", "農曆春節後開始交易日", ""],
        ]}
        self.assertEqual(parse_twse_holidays(payload, 2026),
                         {date(2026, 2, 12), date(2026, 2, 13)})

    def test_market_holiday_uses_review_not_premarket(self):
        context = session_context(datetime(2026, 11, 23, 9, 30, tzinfo=TZ),
                                  closed_dates={date(2026, 11, 23)})
        self.assertEqual(context.report_mode, "weekend_review")
        self.assertFalse(context.is_tw_trading_day)
        self.assertTrue(context.calendar_verified)
        self.assertEqual(context.latest_expected_tw_session, date(2026, 11, 20))

    def test_invalid_official_schedule_fails_not_guesses(self):
        with self.assertRaises(ValueError):
            parse_twse_holidays({"stat": "error"}, 2026)


class MarketEvidenceTests(unittest.TestCase):
    def test_rejects_invented_yearline(self):
        draft = {"watch": "台股年線約在19,000點，因此可能遇到支撐。"}
        issues = unsupported_indicator_issues(draft)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["section"], "watch")

    def test_allows_indicator_without_numeric_guess(self):
        self.assertEqual(unsupported_indicator_issues(
            {"watch": "年線位置需要完整歷史行情計算，暫不提供數字。"}), [])

    def test_fallback_never_invents_numeric_market_claims(self):
        original = {"market": "未知的數字36,000點", "events": "可信的新聞敘述"}
        reduced = safe_redact_sections(original, {"market"})
        self.assertEqual(reduced["events"], original["events"])
        self.assertNotIn("36,000", reduced["market"])

    def test_model_cannot_pass_invented_ma_with_positive_ai_verifier(self):
        now = datetime(2026, 11, 21, 9, 30, tzinfo=TZ)
        draft = {key: "根據已有新聞，市場存在變化。" * 6
                 for key in ("market", "overnight", "events", "flows", "watch")}
        draft["market"] = "大盤目前年線約19,000點。" + draft["market"]
        draft["source_ids"] = [1]
        stages = []
        def answer(messages, **kwargs):
            stages.append(kwargs["stage"])
            if kwargs["stage"] == "stock_brief":
                return draft.copy()
            if kwargs["stage"] == "stock_repair":
                return {"updates": {"market": "大盤均線水位缺少資料，先不提供。" + draft["market"][16:]}}
            return {"supported": True, "issues": []}
        with patch("src.digest_services.editorial._request_parsed_ai", side_effect=answer):
            result = StockService().build({"news": [{
                "title": "市場觀察", "url": "https://example.com/news",
                "description": "市場存在變化", "published_at": now.isoformat(),
            }], "snapshot": []}, [], now)
        self.assertIn("stock_repair", stages)
        self.assertNotIn("19,000點", result.messages[0])
        self.assertIn("週末市場回顧", result.messages[0])


if __name__ == "__main__":
    unittest.main()
