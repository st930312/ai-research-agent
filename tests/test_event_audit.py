"""V4 semantic-event audit contracts: source merging, history and fail-closed."""
import unittest
from unittest.mock import patch

from src.editorial_digest import audit_events


class EventAuditTests(unittest.TestCase):
    def setUp(self):
        self.items = [
            {"id": 1, "category": "tech", "title": "Nvidia investigates CEO connection", "url": "https://one.example/a"},
            {"id": 2, "category": "tech", "title": "Jensen Huang memo disclosed", "url": "https://two.example/b"},
            {"id": 3, "category": "tech", "title": "Investigation into CEO's relationship", "url": "https://three.example/c"},
            {"id": 4, "category": "tech", "title": "Unrelated battery breakthrough", "url": "https://four.example/d"},
        ]

    def test_merges_three_different_headlines_of_one_event(self):
        answer = '{"groups":[{"ids":[1,2,3],"keep":2,"event_type":"investigation","entities":["Nvidia"],"summary":"調查同一事件"},{"ids":[4],"keep":4,"event_type":"release","entities":["Battery"],"summary":"獨立電池技術突破"}],"historical_duplicates":[]}'
        with patch("src.editorial_digest._request_ai", return_value=answer):
            chosen = audit_events(self.items, [], {"calls": 0, "latencies": []})
        self.assertEqual([row["id"] for row in chosen], [2, 4])
        self.assertEqual(chosen[0]["event_summary"], "調查同一事件")
        self.assertEqual(len(chosen[0]["related_urls"]), 3)

    def test_rejects_news_already_in_neon_history(self):
        answer = '{"groups":[{"ids":[4],"keep":4,"event_type":"release","entities":["Battery"],"summary":"獨立電池技術突破"}],"historical_duplicates":[1,2,3]}'
        history = [{"title": "Nvidia investigates Jensen Huang", "category": "tech"}]
        with patch("src.editorial_digest._request_ai", return_value=answer) as request:
            chosen = audit_events(self.items, history, {"calls": 0, "latencies": []})
        self.assertEqual([row["id"] for row in chosen], [4])
        self.assertIn("Nvidia investigates Jensen Huang", request.call_args.args[0][1]["content"])

    def test_fail_closed_when_audit_omits_a_selected_article(self):
        answer = '{"groups":[{"ids":[1,2],"keep":1,"event_type":"investigation","entities":["Nvidia"],"summary":"調查"}],"historical_duplicates":[]}'
        with patch("src.editorial_digest._request_ai", return_value=answer):
            with self.assertRaisesRegex(ValueError, "omitted"):
                audit_events(self.items, [], {"calls": 0, "latencies": []})

    def test_fail_closed_when_same_id_repeated(self):
        answer = '{"groups":[{"ids":[1,2],"keep":1,"event_type":"investigation","entities":["Nvidia"],"summary":"調查"},{"ids":[2,3,4],"keep":3,"event_type":"investigation","entities":["Nvidia"],"summary":"調查"}],"historical_duplicates":[]}'
        with patch("src.editorial_digest._request_ai", return_value=answer):
            with self.assertRaisesRegex(ValueError, "duplicated"):
                audit_events(self.items, [], {"calls": 0, "latencies": []})

    def test_rejects_overmerged_event_group(self):
        items = self.items + [
            {"id": 5, "category": "dev", "title": "Completely unrelated",
             "url": "https://five.example/e"}
        ]
        response = '{"groups":[{"ids":[1,2,3,4,5],"keep":1,"summary":"Wrong grouping",'
        response += '"entities":["Nvidia"],"event_type":"report"}],"historical_duplicates":[]}'
        with patch("src.editorial_digest._request_ai", return_value=response):
            with self.assertRaisesRegex(ValueError, "overmerged"):
                audit_events(items, [], {"calls": 0, "latencies": []})

    def test_missing_semantic_metadata_fails_closed(self):
        response = '{"groups":[{"ids":[1,2,3,4],"keep":1}],"historical_duplicates":[]}'
        with patch("src.editorial_digest._request_ai", return_value=response):
            with self.assertRaisesRegex(ValueError, "summary"):
                audit_events(self.items, [], {"calls": 0, "latencies": []})

    def test_audit_includes_rich_neon_history(self):
        response = '{"groups":[{"ids":[1,2,3,4],"keep":1,"summary":"新事件",'
        response += '"entities":["Nvidia"],"event_type":"report"}],"historical_duplicates":[]}'
        history = [{"title": "舊消息", "category": "tech",
                    "event_summary": "重大安全修補", "event_entities": ["React"],
                    "event_type": "security_fix", "release_tag": "v5.2.0",
                    "repo": "facebook/react", "source_urls": ["https://example.org/source"]}]
        with patch("src.editorial_digest._request_ai", return_value=response) as request:
            audit_events(self.items, history, {"calls": 0, "latencies": []})
        sent = request.call_args.args[0][1]["content"]
        self.assertIn("重大安全修補", sent)
        self.assertIn("v5.2.0", sent)
        self.assertIn("security_fix", sent)

    def test_unrelated_updates_from_same_company_can_survive(self):
        answer = '{"groups":[{"ids":[1],"keep":1,"event_type":"update","entities":["A"],"summary":"事件一"},{"ids":[2],"keep":2,"event_type":"update","entities":["B"],"summary":"事件二"},{"ids":[3],"keep":3,"event_type":"update","entities":["C"],"summary":"事件三"},{"ids":[4],"keep":4,"event_type":"release","entities":["Battery"],"summary":"獨立電池技術突破"}],"historical_duplicates":[]}'
        with patch("src.editorial_digest._request_ai", return_value=answer):
            chosen = audit_events(self.items, [], {"calls": 0, "latencies": []})
        self.assertEqual(len(chosen), 4)


if __name__ == "__main__":
    unittest.main()
