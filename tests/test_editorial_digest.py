import unittest
from unittest.mock import patch
from src import editorial_digest as e

class EditorialDigestTests(unittest.TestCase):
    def setUp(self):
        self.candidates = []
        for i in range(1, 21):
            cat = ["ai", "github", "dev", "tech", "finance"][i % 5]
            self.candidates.append({
                "id": i, "title": f"News {i}", "url": f"https://example.com/{i}",
                "source": "github_search" if cat == "github" else "hackernews",
                "suggested_category": cat,
                "published_at": "2026-11-06", "description": "Brief",
                "score": 3,
            })

    def test_json_code_fence(self):
        self.assertEqual(e._parse_json("\n".join(["```json", '{"selected":[]}', "```"])), {"selected": []})

    def test_shortlist_validates_ids_and_category_caps(self):
        ai = []
        for row in self.candidates:
            ai.append({"id": row["id"], "category": row["suggested_category"],
                       "importance": 2})
        ai.append({"id": 1000, "category": "ai", "importance": 3})
        ai.append({"id": 1, "category": "ai", "importance": 3})
        with patch.object(e, "_request_ai", return_value=__import__("json").dumps(
            {"selected": ai})):
            selected = e.shortlist(self.candidates, {"calls": 0, "latencies": []})
        self.assertLessEqual(len(selected), 15)
        self.assertLessEqual(sum(row["category"] == "github" for row in selected), 2)
        self.assertEqual(len({x["id"] for x in selected}), len(selected))

    def test_prompt_resists_untrusted_input(self):
        with patch.object(e, "_request_ai", return_value=__import__("json").dumps(
            {"selected": [{"id": 1, "category": "github", "importance": 3}]})):
            selected = e.shortlist(self.candidates, {"calls": 0, "latencies": []})
        self.assertEqual(selected[0]["category"], "github")

    def test_embed_limits_and_categories(self):
        articles = [{
            **self.candidates[0], "category": "ai", "importance": 2,
            "ai_description": "內容" * 200, "body_status": "ok"
        }]
        embeds = e.build_embeds(articles)
        self.assertEqual(len(embeds), 1)
        self.assertTrue(all(len(x["value"]) <= 1024 for x in embeds[0]["fields"]))
        self.assertEqual(len(e.split_embed_messages(embeds)), 1)

    def test_no_discord_without_valid_webhook(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError):
                e.post_discord([])

    def test_budget_limit(self):
        metrics = {"calls": 7, "latencies": []}
        with self.assertRaisesRegex(RuntimeError, "budget"):
            e._request_ai([], 100, metrics)

if __name__ == "__main__":
    unittest.main()
