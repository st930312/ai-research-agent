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
            return '{"articles":[{"id":1,"description":"全球產業需求、供應鏈與監管趨勢的整理。"}]}'
        with patch("src.editorial_digest._request_ai", side_effect=fake_ai), \
             patch("src.editorial_digest.enrich", side_effect=lambda row: {**row, "body_status": "ok"}):
            result = draft(cap_selection(rows), {"calls": 0, "latencies": []})
        self.assertEqual(result[0]["title"], "全球半導體與金融科技產業觀察")
        self.assertEqual(result[0]["published_title"], rows[0]["title"])
        request = captured["messages"][1]["content"]
        for row in rows:
            self.assertIn(row["url"], request)
        self.assertIn("不要台股買賣建議", captured["messages"][0]["content"])

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

    def test_finance_and_games_get_verified_reserve_candidates(self):
        now = "2026-11-09T05:00:00+00:00"
        raw = [
            {"id": 1, "title": "Major semiconductor wafer equipment demand",
             "url": "https://example.org/semiconductor", "source": "rss",
             "suggested_category": "tech", "published_at": now},
            {"id": 2, "title": "Digital banking payments regulation in Europe",
             "url": "https://example.org/banking", "source": "rss",
             "suggested_category": "finance", "published_at": now},
            {"id": 3, "title": "Distinctive mobile game global launch",
             "url": "https://example.org/mobile", "source": "rss",
             "suggested_category": "gaming", "published_at": now},
            {"id": 4, "title": "Original Steam game launch",
             "url": "https://example.org/pc", "source": "rss",
             "suggested_category": "gaming", "published_at": now},
            {"id": 5, "title": "TechCrunch Founder Summit 2026",
             "url": "https://example.org/summit", "source": "rss",
             "suggested_category": "finance", "published_at": now},
        ]
        with patch("src.editorial_digest._request_ai",
                   return_value='{"selected":[]}'):
            picks = shortlist(raw, {"calls": 0, "latencies": []},
                              target=20, oversample=True)
        finance = [x for x in picks if x["category"] == "finance"]
        games = [x for x in picks if x["category"] == "gaming"]
        self.assertEqual(len(finance), 2)
        self.assertEqual(len(games), 2)
        self.assertFalse(any("Founder Summit" in x["title"] for x in finance))

    def test_category_quota_is_one_slot_per_roundup(self):
        self.assertEqual(CATEGORIES["finance"][1], 1)
        self.assertEqual(CATEGORIES["gaming"][1], 1)


if __name__ == "__main__":
    unittest.main()
