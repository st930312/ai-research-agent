"""V5 parallel services and shared NVIDIA queue regression coverage."""
import json
import threading
import time
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src.ai_scheduler import AIRequestScheduler
from src.digest_v5 import DigestOrchestrator
from src.digest_services import DigestResult, StockService, TechService, GamingService
from src import editorial_digest as editorial


class V5Tests(unittest.TestCase):
    def test_scheduler_is_fifo_and_never_overlaps_http_attempts(self):
        scheduler = AIRequestScheduler(min_interval=0)
        barrier = threading.Barrier(3)
        active = 0
        maximum = 0
        processed = []
        lock = threading.Lock()

        def task(index):
            nonlocal active, maximum
            barrier.wait()
            def request():
                nonlocal active, maximum
                with lock:
                    active += 1
                    maximum = max(maximum, active)
                time.sleep(0.004)
                with lock:
                    processed.append(index)
                    active -= 1
                return index
            return scheduler.run(request, label=str(index))

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as pool:
            outputs = list(pool.map(task, (1, 2, 3)))
        self.assertEqual(set(outputs), {1, 2, 3})
        self.assertEqual(set(processed), {1, 2, 3})
        self.assertEqual(maximum, 1)

    def test_scheduler_spacing_between_requests(self):
        times = []
        scheduler = AIRequestScheduler(min_interval=0.02)
        scheduler.run(lambda: times.append(time.monotonic()))
        scheduler.run(lambda: times.append(time.monotonic()))
        self.assertGreaterEqual(times[1] - times[0], 0.018)

    def test_scheduler_cooldown_begins_after_completion(self):
        scheduler = AIRequestScheduler(min_interval=0.02)
        finished = []
        started = []
        def first():
            time.sleep(0.008)
            finished.append(time.monotonic())
        scheduler.run(first)
        scheduler.run(lambda: started.append(time.monotonic()))
        self.assertGreaterEqual(started[0] - finished[0], 0.018)

    def test_legacy_collector_excludes_other_service_feeds(self):
        with patch("src.editorial_digest.hn_latest", return_value=[]), \
             patch("src.editorial_digest.github_discover", return_value=[]), \
             patch("src.editorial_digest.github_releases", return_value=([], {})), \
             patch("src.editorial_digest.rss_discover", return_value=([], {})) as rss:
            editorial.collect_candidates(categories={"gaming"})
        self.assertEqual(rss.call_args.kwargs["categories"], {"gaming"})

    def test_stock_sources_are_kept_outside_tech_quota(self):
        service = StockService()
        now = datetime(2026, 11, 20, 8, 30, tzinfo=ZoneInfo("Asia/Taipei"))
        news = [{
            "title": "美股重挫拖累台股", "description": "美股與半導體市場承壓",
            "url": "https://example.com/market-down",
            "published_at": now.isoformat(), "publisher": "中央社",
            "suggested_category": "tw_stock", "source": "rss"
        }]
        response = {
            "market": "台灣市場昨日出現顯著波動；部分收盤資料仍待核對。" * 4,
            "overnight": "美國科技股受壓，但尚未確認收盤數字。" * 3,
            "events": "國際半導體政策變化可能影響本地產業，需以正式公告為準。" * 3,
            "flows": "法人買賣超確切數據缺失，不能填入猜測數字。" * 3,
            "watch": "今日觀察海外科技股、匯率及類股風險，不構成買賣建議。" * 3,
            "source_ids": [1],
        }
        def model_answer(*args, **kwargs):
            if kwargs.get("stage") == "stock_verify":
                return {"supported": True, "issues": []}
            return response
        with patch("src.digest_services.editorial._request_parsed_ai",
                   side_effect=model_answer) as model:
            result = service.build({"news": news, "snapshot": []}, [], now)
        self.assertEqual(result.service, "stock")
        self.assertEqual(len(result.messages), 1)
        self.assertLessEqual(len(result.messages[0]), 1900)
        self.assertIn("美股與夜盤", result.messages[0])
        self.assertIn("https://example.com/market-down", result.messages[0])
        self.assertEqual(result.daily_identity, "2026-11-20")
        self.assertEqual(result.articles, [])
        self.assertTrue(model.called)

    def test_stock_brief_missing_evidence_blocks_publication(self):
        service = StockService()
        now = datetime(2026, 11, 20, 8, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        response = {field: "有文字" * 50 for field in
                    ("market", "overnight", "events", "flows", "watch")}
        response["source_ids"] = []
        with patch("src.digest_services.editorial._request_parsed_ai",
                   return_value=response):
            with self.assertRaisesRegex(RuntimeError, "STOCK_BRIEF_INCOMPLETE"):
                service.build({"news": [{"title": "台股",
                     "url": "https://example.com/1",
                     "published_at": now.isoformat()}], "snapshot": []}, [], now)

    def test_stock_rejects_unsupported_claims_before_publication(self):
        service = StockService()
        now = datetime(2026, 11, 20, 15, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        payload = {key: "市場有消息，需要以正式來源進行核對。" * 5
                   for key in ("market", "overnight", "events", "flows", "watch")}
        payload["source_ids"] = [1]
        source = {"title": "台股市場", "description": "市場觀察",
                  "url": "https://example.com/market",
                  "published_at": now.isoformat()}
        calls = []
        def model_answer(*args, **kwargs):
            calls.append(kwargs.get("stage"))
            if kwargs.get("stage") == "stock_verify":
                return {"supported": False, "issues": ["沒有來源支持的人事斷言"]}
            return payload
        with patch("src.digest_services.editorial._request_parsed_ai",
                   side_effect=model_answer):
            with self.assertRaisesRegex(RuntimeError, "unsupported_claims"):
                service.build({"news": [source], "snapshot": []}, [], now)
        self.assertEqual(calls,
                         ["stock_brief", "stock_verify", "stock_brief", "stock_verify"])

    def test_gaming_format_omits_generic_technology_summary(self):
        from src.wide_discord import format_wide_messages
        articles = [{
            "id": 1, "title": "今日遊戲情報精選",
            "url": "https://example.com/game",
            "category": "gaming", "body_status": "ok",
            "ai_description": "### 遊戲一\\n\\n" + ("實際內容及玩法重點。" * 20),
        }]
        messages = format_wide_messages(
            articles, {"gaming": editorial.CATEGORIES["gaming"]},
            issue_date=datetime(2026, 11, 20).date(), include_summary=False)
        self.assertEqual(len(messages), 1)
        self.assertIn("今日遊戲情報精選", messages[0])
        self.assertNotIn("科技快訊", messages[0])

    def test_failure_of_one_service_does_not_block_others(self):
        class Good:
            name = "good"
            def collect(self):
                return [{"title": "a"}]
            def build(self, candidates, history, now):
                return DigestResult("good", [], ["hello"], {"calls": 0})
        class Bad:
            name = "bad"
            def collect(self):
                raise RuntimeError("source unavailable")
        scheduler = AIRequestScheduler(min_interval=0)
        with self.assertRaisesRegex(RuntimeError, "V5_PARTIAL_FAILURE"):
            DigestOrchestrator(
                services=[Bad(), Good()], scheduler=scheduler
            ).run(live_ai=True, send_discord=False)
        self.assertIsNone(editorial._AI_REQUEST_SCHEDULER)

    def test_scheduler_hook_is_used_by_nvidia_stream(self):
        import io
        from unittest.mock import MagicMock
        response = MagicMock()
        packet = {"choices": [{"delta": {"content": '{"ok":true}'}}]}
        response.__enter__.return_value.__iter__.return_value = iter([
            ("data: " + json.dumps(packet) + "\n").encode(),
            b"data: [DONE]\n"
        ])
        class ImmediateScheduler:
            def __init__(self):
                self.calls = 0
            def run(self, action, *, label):
                self.calls += 1
                return action()
        scheduler = ImmediateScheduler()
        with patch("src.editorial_digest._AI_REQUEST_SCHEDULER", scheduler), \
             patch.dict("os.environ", {"NVIDIA_API_KEY": "test"}), \
             patch("src.editorial_digest.urllib.request.urlopen",
                   return_value=response):
            result = editorial._request_ai(
                [], 100, {"calls": 0, "latencies": []})
        self.assertEqual(result, '{"ok":true}')
        self.assertEqual(scheduler.calls, 1)


if __name__ == "__main__":
    unittest.main()
