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
        with patch("src.editorial_digest.enrich",side_effect=lambda x:{**x,"body_status":"ok"}),\
             patch("src.editorial_digest._request_ai",return_value=
                   '{"articles":[{"id":1,"description":"新聞摘要內容較短"}]}'):
            with self.assertRaisesRegex(RuntimeError,"INCOMPLETE_AI_BODY"):
                draft(rows,{"calls":0,"latencies":[]})

    def test_model_omitted_last_article_fails_closed(self):
        rows=[self.row(1),self.row(2,"finance")]
        long="事件及產業影響分析。"*35
        import json
        with patch("src.editorial_digest.enrich",side_effect=lambda x:{**x,"body_status":"ok"}),\
             patch("src.editorial_digest._request_ai",return_value=json.dumps({
                 "articles":[{"id":1,"description":long}]},ensure_ascii=False)):
            with self.assertRaisesRegex(RuntimeError,"INCOMPLETE_AI_BODY"):
                draft(rows,{"calls":0,"latencies":[]})

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
