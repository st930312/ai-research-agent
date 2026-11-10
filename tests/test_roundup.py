"""V4.1 industry and game roundups: coverage, evidence, and persistence."""
import unittest
from unittest.mock import patch

from src.editorial_digest import CATEGORIES, cap_selection, draft, shortlist
from src.wide_discord import article_text


class RoundupTests(unittest.TestCase):
    def sample(self, category, ident, title):
        return {
            "id": ident, "category": category, "title": title,
            "url": f"https://example.org/{category}/{ident}",
            "source": "rss", "description": "source excerpt", "importance": 2,
            "suggested_category": category,
            "publisher": "TechCrunch Fintech" if category == "finance" else "巴哈姆特 GNN",
            "event_summary": f"Event {ident}",
        }

    def test_single_finance_slot_combines_three_independent_events(self):
        rows = [self.sample("finance", n, f"Global semiconductor news {n}") for n in (1, 2, 3)]
        result = cap_selection(rows)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]["roundup_sources"]), 2)
        self.assertEqual(set(result[0]["related_urls"]),
                         {rows[1]["url"], rows[2]["url"]})

    def test_game_roundup_includes_mobile_and_pc_not_only_one_game(self):
        rows = [self.sample("gaming", 1, "Major Steam platform change"),
                self.sample("gaming", 2, "Original mobile RPG launch"),
                self.sample("gaming", 3, "New Nintendo handheld title")]
        result = cap_selection(rows)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]["roundup_sources"]), 2)
        msg = article_text({**result[0], "ai_description": "三則有趣遊戲消息"}, 1)
        for source in rows:
            self.assertIn(source["url"], msg)
        self.assertEqual(msg.count("🔗 延伸來源"), 2)

    def test_roundup_draft_requests_all_sources_and_uses_column_title(self):
        rows = [self.sample("finance", 1, "Major semiconductor equipment order"),
                self.sample("finance", 2, "HBM memory supply chain capacity"),
                self.sample("finance", 3, "Fintech payment regulation changes")]
        captured = {}
        def fake_ai(messages, max_tokens, metrics):
            captured["messages"] = messages
            return __import__("json").dumps({"articles":[{"id":1,"description":"全球產業供應鏈與監管的重要事件，需以資料來源逐項核對、區分已確認事實和產業推論。" * 6}]},ensure_ascii=False)
        with patch("src.editorial_digest._request_ai", side_effect=fake_ai), \
             patch("src.editorial_digest.enrich", side_effect=lambda row: {**row, "body_status": "ok"}):
            result = draft(cap_selection(rows), {"calls": 0, "latencies": []})
        self.assertEqual(result[0]["title"], "全球半導體與金融科技產業觀察")
        self.assertEqual(result[0]["published_title"], rows[0]["title"])
        request = captured["messages"][1]["content"]
        for row in rows:
            self.assertIn(row["url"], request)
        self.assertIn("不提供個股推薦", captured["messages"][0]["content"])
        self.assertIn("具體事件", captured["messages"][0]["content"])


    def test_finance_roundup_keeps_ai_markdown_subheadings(self):
        body = ("總覽：本期觀察多項互不相關的產業事件。\\n\\n"
                "### 晶片供應鏈動態\\n\\n第一個事件有明確的來源證據。\\n\\n"
                "### 跨境支付監管\\n\\n第二個事件獨立呈現。\\n\\n"
                "### 產業觀察\\n\\n目前只比較已確認的事實。")
        row = self.sample("finance", 1, "Industry events")
        rendered = article_text({**row, "ai_description": body}, 1)
        self.assertIn("### 晶片供應鏈動態", rendered)
        self.assertIn("### 跨境支付監管", rendered)
        self.assertIn("### 產業觀察", rendered)
        self.assertIn("\\n\\n### ", rendered)

    def test_finance_roundup_model_gets_layout_and_extended_length_instructions(self):
        rows = [self.sample("finance", n, f"Industry story {n}") for n in (1, 2, 3)]
        captured = {}
        description = ("總覽：三則獨立產業事件。\\n\\n"
                       "### 半導體事件\\n\\n具體內容與發展。\\n\\n"
                       "### 金融科技事件\\n\\n政策與監管動向。\\n\\n"
                       "### 產業觀察\\n\\n未確定的影響仍需觀察。") * 9
        def fake_ai(messages, max_tokens, metrics):
            captured["prompt"] = messages[0]["content"]
            captured["max_tokens"] = max_tokens
            return __import__("json").dumps(
                {"articles": [{"id": 1, "description": description}]},
                ensure_ascii=False)
        with patch("src.editorial_digest._request_ai", side_effect=fake_ai), \\
             patch("src.editorial_digest.enrich",
                   side_effect=lambda row: {**row, "body_status": "ok"}):
            result = draft(cap_selection(rows), {"calls": 0, "latencies": []})
        self.assertIn("700～1100", captured["prompt"])
        self.assertIn("### 事件小標題", captured["prompt"])
        self.assertIn("事件之間留空行", captured["prompt"])
        self.assertGreater(captured["max_tokens"], 4400)
        self.assertGreater(len(result[0]["ai_description"]), 650)
        self.assertLessEqual(len(result[0]["ai_description"]), 1600)

    def test_very_long_finance_article_split_without_losing_headings(self):
        from src.wide_discord import format_wide_messages
        long_body = ("### 供應鏈\\n\\n" + "背景與事件。" * 170
                     + "\\n\\n### 產業觀察\\n\\n" + "產業影響。" * 160)
        row = self.sample("finance", 1, "Industry review")
        result = format_wide_messages(
            [{**row, "ai_description": long_body}],
            CATEGORIES)
        self.assertTrue(all(len(message) <= 2000 for message in result))
        combined = "".join(result)
        self.assertIn("### 供應鏈", combined)
        self.assertIn("### 產業觀察", combined)

    def test_game_not_filled_from_low_priority_metadata(self):
        now = "2026-11-09T05:00:00+00:00"
        rows = [
            {"id":1, "title":"Ordinary mobile preregistration", "source":"rss",
             "url":"https://example.org/game", "published_at":now,
             "suggested_category":"gaming"},
            {"id":2, "title":"Cloud storage architecture", "source":"rss",
             "url":"https://example.org/dev", "published_at":now,
             "suggested_category":"dev"},
        ]
        with patch("src.editorial_digest._request_ai",
                   return_value='{"selected":[{"id":2,"category":"dev","importance":2}]}'):
            result = shortlist(rows, {"calls": 0, "latencies":[]})
        self.assertFalse(any(row["category"] == "gaming" for row in result))

    def test_flexible_slot_requires_high_quality_approved_article(self):
        base = [self.sample("ai", n, f"AI story {n}") for n in range(1, 6)]
        for row in base:
            row["importance"] = 3
        chosen = cap_selection(base)
        self.assertEqual(len(chosen), 5)  # AI quota four plus one optional flex
        self.assertEqual(sum(x["category"] == "ai" for x in chosen), 5)

    def test_weak_flexible_candidate_not_forced(self):
        base = [self.sample("ai", n, f"AI story {n}") for n in range(1, 6)]
        base[-1]["importance"] = 1
        chosen = cap_selection(base)
        self.assertEqual(len(chosen), 4)

    def test_finance_reserve_trusted_feeds_without_title_keywords(self):
        now = "2026-11-09T05:00:00+00:00"
        rows = [
            {"id":1, "title":"Factory capacity outlook unexpectedly changed",
             "url":"https://example.org/a", "source":"rss",
             "publisher":"Semiconductor Engineering",
             "suggested_category":"finance","published_at":now},
            {"id":2, "title":"European banking oversight update",
             "url":"https://example.org/b", "source":"rss",
             "publisher":"TechCrunch Fintech",
             "suggested_category":"finance","published_at":now},
            {"id":3, "title":"Unrelated developer summit",
             "url":"https://example.org/c", "source":"rss",
             "publisher":"Unrelated publisher",
             "suggested_category":"finance","published_at":now},
        ]
        with patch("src.editorial_digest._request_ai",return_value='{"selected":[]}'):
            picks=shortlist(rows,{"calls":0,"latencies":[]},target=20,oversample=True)
        finance=[p for p in picks if p["category"]=="finance"]
        self.assertEqual(len(finance),2)
        self.assertFalse(any("summit" in p["title"] for p in finance))

    def test_game_no_keyword_can_be_selected_in_shared_ai(self):
        now="2026-11-09T05:00:00+00:00"
        row={"id":1,"title":"Astral Tide: Echoes chapter expansion",
            "url":"https://example.org/a", "source":"rss",
            "suggested_category":"gaming", "publisher":"Gematsu",
            "published_at":now}
        with patch("src.editorial_digest._request_ai",return_value=
                   '{"selected":[{"id":1,"category":"gaming","importance":3}]}'):
            chosen=shortlist([row],{"calls":0,"latencies":[]})
        self.assertEqual(len(cap_selection(chosen)),1)

    def test_category_quota_is_one_slot_per_roundup(self):
        self.assertEqual(CATEGORIES["finance"][1], 1)
        self.assertEqual(CATEGORIES["gaming"][1], 1)


if __name__ == "__main__":
    unittest.main()
