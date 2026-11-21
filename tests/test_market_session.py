"""Regression tests for Taiwan stock briefing timing and quote context."""
import json
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src.market_session import session_context
from src.digest_services import StockService, fetch_market_snapshot


TZ = ZoneInfo("Asia/Taipei")


class SessionTests(unittest.TestCase):
    def test_friday_early_session_uses_premarket_lens_not_premarket_label(self):
        ctx = session_context(datetime(2026, 11, 20, 9, 30, tzinfo=TZ))
        self.assertEqual(ctx.report_mode, "early_session")
        self.assertEqual(ctx.heading, "台股開盤初期情報")
        self.assertEqual(str(ctx.latest_expected_tw_session), "2026-11-19")
        self.assertIn("盤前", ctx.editorial_lens)

    def test_saturday_uses_weekend_review_friday_close(self):
        ctx = session_context(datetime(2026, 11, 21, 8, 28, tzinfo=TZ))
        self.assertEqual(ctx.report_mode, "weekend_review")
        self.assertEqual(ctx.heading, "台股週末市場回顧")
        self.assertEqual(str(ctx.latest_expected_tw_session), "2026-11-20")
        self.assertFalse(ctx.is_tw_trading_day)

    def test_monday_premarket_expects_friday(self):
        ctx = session_context(datetime(2026, 11, 23, 8, 30, tzinfo=TZ))
        self.assertEqual(ctx.report_mode, "premarket")
        self.assertEqual(str(ctx.latest_expected_tw_session), "2026-11-20")

    def test_intraday_and_postmarket(self):
        self.assertEqual(session_context(datetime(2026, 11, 23, 11, tzinfo=TZ)).report_mode, "intraday")
        self.assertEqual(session_context(datetime(2026, 11, 23, 14, tzinfo=TZ)).report_mode, "postmarket")

    def test_market_snapshot_has_date_and_prior_close(self):
        import urllib.parse
        from datetime import datetime, timezone
        def ts(day):
            return int(datetime(2026, 11, day, 13, 30, tzinfo=TZ).timestamp())
        sample = {"chart": {"result": [{"timestamp": [ts(19), ts(20)],
                  "indicators": {"quote": [{"close": [38000.0, 36000.0]}]}}]}}
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, *_):
                return json.dumps(sample).encode("utf-8")
        rows = fetch_market_snapshot(fetcher=lambda req, timeout: FakeResponse())
        self.assertEqual(len(rows), 5)
        tw = next(r for r in rows if r["symbol"] == "^TWII")
        self.assertEqual(tw["session_date"], "2026-11-20")
        self.assertEqual(tw["previous_close"], 38000)
        self.assertEqual(tw["change"], -2000)
        self.assertAlmostEqual(tw["change_pct"], -5.26)

    def test_sunday_editorial_guidance_is_explainable_and_conditional(self):
        now = datetime(2026, 11, 22, 8, 30, tzinfo=TZ)
        draft = {key: "已有新聞指出市場出現變化，後續仍有待觀察。" * 6
                 for key in ("market", "overnight", "events", "flows", "watch")}
        draft["source_ids"] = [1]
        seen = []
        def answer(messages, **kwargs):
            if kwargs["stage"] == "stock_brief":
                seen.append(messages[0]["content"])
                return draft
            return {"supported": True, "issues": []}
        with patch("src.digest_services.editorial._request_parsed_ai",
                   side_effect=answer):
            result = StockService().build({"news": [{
                "title": "市場消息", "description": "市場變化",
                "url": "https://example.com/stock",
                "published_at": now.isoformat()}], "snapshot": []}, [], now)
        self.assertIn("台股週末市場回顧", result.messages[0])
        self.assertIn("下個交易日觀察", result.messages[0])
        self.assertIn("發生什麼、為何重要", seen[0])
        self.assertIn("2～3 項具體可觀察", seen[0])
        self.assertIn("不可推薦個股買賣", seen[0])

    def test_stock_prompt_has_session_mode(self):
        now = datetime(2026, 11, 20, 9, 30, tzinfo=TZ)
        draft = {key: "依資料觀察，市場仍需注意國際消息。" * 7
                 for key in ("market", "overnight", "events", "flows", "watch")}
        draft["source_ids"] = [1]
        seen = []
        def answer(messages, **kwargs):
            if kwargs["stage"] == "stock_brief":
                seen.append((messages[0]["content"], json.loads(messages[1]["content"])))
                return draft
            return {"supported": True, "issues": []}
        with patch("src.digest_services.editorial._request_parsed_ai", side_effect=answer):
            result = StockService().build({"news": [{"title": "市場新聞",
                "description": "國際市場波動", "url": "https://example.com/news",
                "published_at": now.isoformat()}], "snapshot": []}, [], now)
        self.assertIn("台股開盤初期情報", result.messages[0])
        self.assertIn("今日盤勢觀察", result.messages[0])
        self.assertEqual(seen[0][1]["report_mode"], "early_session")
        self.assertIn("禁止自行估算年線", seen[0][0])


if __name__ == "__main__":
    unittest.main()
