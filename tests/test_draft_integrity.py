"""Regression: missing AI descriptions must never reach Discord."""
import unittest
from unittest.mock import patch
from src.editorial_digest import draft, validate_draft_bodies
from src.wide_discord import article_text

class DraftIntegrityTests(unittest.TestCase):
    def row(self, ident, category="gaming"):
        return {
            "id":ident, "category":category, "title":"Test topic",
            "url":f"https://example.org/{ident}", "source":"rss",
            "importance":2, "description":"Verified factual source summary",
        }

    def test_partial_model_batch_fails_closed(self):
        rows=[self.row(1),self.row(2,"finance")]
        with patch("src.editorial_digest.time.sleep"), \
             patch("src.editorial_digest.enrich",side_effect=lambda x:{**x,"body_status":"ok"}),\
             patch("src.editorial_digest._request_ai",return_value=
                   '{"articles":[{"id":1,"description":"新聞摘要內容較短"}]}'):
            with self.assertRaisesRegex(RuntimeError,"INCOMPLETE_AI_BODY"):
                draft(rows,{"calls":0,"latencies":[]})

    def test_model_omitted_last_article_fails_closed(self):
        rows=[self.row(1),self.row(2,"finance")]
        long="事件及產業影響分析。"*35
        import json
        with patch("src.editorial_digest.time.sleep"), \
             patch("src.editorial_digest.enrich",side_effect=lambda x:{**x,"body_status":"ok"}),\
             patch("src.editorial_digest._request_ai",return_value=json.dumps({
                 "articles":[{"id":1,"description":long}]},ensure_ascii=False)):
            with self.assertRaisesRegex(RuntimeError,"INCOMPLETE_AI_BODY"):
                draft(rows,{"calls":0,"latencies":[]})


    def test_only_missing_article_retried_with_backoff(self):
        import json
        rows = [self.row(1, "ai"), self.row(2, "finance")]
        body = "真實來源事件與背景。" * 35
        requests = []
        def fake_ai(messages, max_tokens, metrics):
            requests.append(json.loads(messages[1]["content"]))
            if len(requests) == 1:
                return json.dumps({"articles": [{"id": 2, "description": body}]},
                                  ensure_ascii=False)
            return json.dumps({"articles": [{"id": 1, "description": body}]},
                              ensure_ascii=False)
        with patch("src.editorial_digest.time.sleep") as sleeper, \
             patch("src.editorial_digest.enrich",
                   side_effect=lambda x: {**x, "body_status": "ok"}), \
             patch("src.editorial_digest._request_ai", side_effect=fake_ai):
            result = draft(rows, {"calls": 0, "latencies": []})
        self.assertEqual([row["id"] for row in result], [1, 2])
        self.assertEqual([x["id"] for x in requests[1]], [1])
        sleeper.assert_called_once()

    def test_three_retries_then_fail_closed(self):
        import json
        calls = []
        def incomplete(messages, max_tokens, metrics):
            calls.append(1)
            return json.dumps({"articles": []})
        with patch("src.editorial_digest.time.sleep") as sleeper, \
             patch("src.editorial_digest.enrich",
                   side_effect=lambda x: {**x, "body_status": "ok"}), \
             patch("src.editorial_digest._request_ai", side_effect=incomplete):
            with self.assertRaisesRegex(RuntimeError, "INCOMPLETE_AI_BODY"):
                draft([self.row(1, "finance")], {"calls": 0, "latencies": []})
        self.assertEqual(len(calls), 4)
        self.assertEqual(sleeper.call_count, 3)

    def test_renderer_rejects_missing_body(self):
        with self.assertRaisesRegex(ValueError,"no real body"):
            article_text(self.row(1),1)

    def test_pre_send_guard_rejects_placeholders(self):
        with self.assertRaisesRegex(RuntimeError,"Placeholder"):
            validate_draft_bodies([{
                **self.row(1),"ai_description":"本則 AI 摘要未完整產生，請閱讀來源。" * 10,
            }])

    def test_long_real_body_passes(self):
        validate_draft_bodies([{
            **self.row(1), "ai_description":"已報導事件及具體影響。"*24
        }])

if __name__ == "__main__":
    unittest.main()
