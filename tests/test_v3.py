import unittest
from datetime import datetime, timezone, timedelta, date
from unittest.mock import patch
from src.v3_sources import github_releases, event_dedup
from src.editorial_digest import _parse_json, CATEGORIES as REAL_CATEGORIES, shortlist
from src.wide_discord import format_wide_messages

CATEGORIES = {
    "ai": ("🤖 AI / LLM / Agent", 4, 0),
    "github": ("🧰 GitHub 開源推薦", 2, 0),
    "dev": ("🛠️ 軟體工程 / DevOps", 2, 0),
    "tech": ("🚀 科技產業 / 新技術", 4, 0),
    "gaming": ("🎮 電玩 / 遊戲產業", 2, 0),
    "finance": ("📊 金融科技 / 半導體", 1, 0),
}

class V3Tests(unittest.TestCase):
    def test_first_discord_title_includes_taiwan_issue_date(self):
        messages = format_wide_messages([], REAL_CATEGORIES, issue_date=date(2026, 11, 9))
        self.assertIn("# 🛰️ 2026/11/09 科技快訊", messages[0])
        self.assertEqual(len(messages), 1)

    def test_taiwan_stock_quota_and_category(self):
        self.assertEqual(sum(x[1] for x in REAL_CATEGORIES.values()), 15)
        self.assertEqual(REAL_CATEGORIES["tw_stock"][1], 1)
        sample = [
            {"id": 1, "title": "航運族群因運價變動受市場關注",
             "url": "https://example.com/taiwan-shipping",
             "suggested_category": "tw_stock", "source": "rss",
             "published_at": datetime.now(timezone.utc).isoformat()},
            {"id": 2, "title": "AI model launch", "url": "https://example.org/ai",
             "suggested_category": "ai", "source": "rss",
             "published_at": datetime.now(timezone.utc).isoformat()},
        ]
        with patch("src.editorial_digest._request_ai", return_value=
                   '{"selected":[{"id":1,"category":"tech","importance":3},'
                   '{"id":2,"category":"tw_stock","importance":3}]}'):
            picks = shortlist(sample, {"calls": 0, "latencies": []})
        self.assertEqual(len([p for p in picks if p["category"] == "tw_stock"]), 1)
        self.assertEqual([p["id"] for p in picks if p["category"] == "tw_stock"], [1])

    def test_model_json_with_trailing_text(self):
        parsed = _parse_json('{"articles":[{"id":1,"description":"正常"}]}'
                             '{"note":"unrequested trailing object"}')
        self.assertEqual(parsed["articles"][0]["id"], 1)
        self.assertEqual(_parse_json("Here is the JSON: " +
                                     '{"selected":[{"id":3}]}')['selected'][0]['id'], 3)

    def test_release_filter(self):
        date = datetime.now(timezone.utc).isoformat()
        def fake(_):
            return [
                {"tag_name": "v1.9.0", "name": "Stable", "html_url":
                 "https://github.com/golang/go/releases/tag/v1.9.0",
                 "published_at": date, "body": "Important"},
                {"tag_name": "v2.0.0-beta1", "name": "Beta", "html_url":
                 "https://github.com/golang/go/releases/tag/v2.0.0-beta1",
                 "prerelease": True, "published_at": date},
            ]
        with patch("src.v3_sources.TRACKED_REPOS", ("golang/go",)):
            rows, counts = github_releases(fetcher=fake)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "github_release")
        self.assertEqual(counts["golang/go"], 1)

    def test_different_release_versions_survive_title_similarity_filter(self):
        rows = [
            {"source": "github_release", "repo": "owner/long-project-name",
             "tag": "v2.0.0", "title": "owner/long-project-name releases v2.0.0",
             "url": "https://github.com/owner/long-project-name/releases/tag/v2.0.0"},
            {"source": "github_release", "repo": "owner/long-project-name",
             "tag": "v2.0.1", "title": "owner/long-project-name releases v2.0.1",
             "url": "https://github.com/owner/long-project-name/releases/tag/v2.0.1"},
        ]
        self.assertEqual(len(event_dedup(rows)), 2)

    def test_cross_source_similar_headline_dedup(self):
        rows = [
            {"url": "https://a.com/story", "title": "Example launches technology"},
            {"url": "https://b.com/story", "title": "Example launches technology"},
            {"url": "https://c.com/story", "title": "Independent news event"},
            {"url": "https://a.com/story?utm_source=x", "title": "Example launches technology"},
        ]
        self.assertEqual(len(event_dedup(rows)), 2)

    def test_wide_separates_categories_and_has_spacing(self):
        rows = [
            {"category": "ai", "title": "First story", "url": "https://example.org/a",
             "ai_description": "內容" * 180, "body_status": "ok"},
            {"category": "gaming", "title": "Steam release", "url": "https://example.org/b",
             "ai_description": "新的遊戲" * 60, "body_status": "ok"},
        ]
        messages = format_wide_messages(rows, CATEGORIES)
        self.assertGreaterEqual(len(messages), 3)
        self.assertTrue(messages[0].startswith("\u200b\n\n"))
        self.assertTrue(any(msg.endswith("\n\n\u200b") for msg in messages))
        self.assertTrue(all(len(msg) < 2000 for msg in messages))
        self.assertTrue(any("## 01｜First story" in msg for msg in messages))
        self.assertTrue(any("# 🎮" in msg for msg in messages))

    def test_same_category_continuations_have_one_heading_without_spacers(self):
        rows = [{
            "category": "tech", "title": f"Technology story {n}",
            "url": f"https://example.org/story-{n}",
            "ai_description": "技術敘述" * 115,
            "body_status": "ok",
        } for n in range(1, 5)]
        messages = format_wide_messages(rows, CATEGORIES)
        category_messages = [m for m in messages if "Technology story" in m or "# 🚀" in m]
        self.assertGreater(len(category_messages), 1)
        self.assertEqual(sum(m.count("# 🚀 科技產業") for m in messages), 1)
        self.assertTrue(category_messages[0].startswith("\u200b\n\n# 🚀"))
        self.assertFalse(category_messages[0].endswith("\n\n\u200b"))
        self.assertFalse(category_messages[1].startswith("\u200b\n\n"))
        self.assertTrue(category_messages[-1].endswith("\n\n\u200b"))
        self.assertEqual(sum(m.count("🔗 來源：") for m in category_messages), 4)

    def test_long_article_is_not_discarded(self):
        long = "很長的文章" * 500
        row = {"category": "ai", "title": "Title", "url": "https://example.org/a",
               "ai_description": long, "body_status": "ok"}
        messages = format_wide_messages([row], CATEGORIES)
        self.assertGreaterEqual(len(messages), 3)
        self.assertTrue(all(len(msg) <= 2000 for msg in messages))
        self.assertEqual("".join(messages).count("很"), 500)

if __name__ == "__main__":
    unittest.main()
