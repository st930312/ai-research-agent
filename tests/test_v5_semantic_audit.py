"""Contiguous local IDs and recovery from malformed semantic duplicate decisions."""
import json
import unittest
from unittest.mock import patch
from src.editorial_digest import audit_events


class LocalAuditTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"id": 5, "category": "tech", "title": "Orion launches new chips",
             "url": "https://example.org/a"},
            {"id": 27, "category": "tech", "title": "Orion unveils chip lineup",
             "url": "https://example.org/b"},
            {"id": 48, "category": "dev", "title": "Editor releases security patch",
             "url": "https://example.org/c"},
        ]

    def good(self):
        return {"decisions": [
            {"id": 1, "action": "keep",
             "summary": "Orion 發表晶片", "event_type": "launch",
             "entities": ["Orion"]},
            {"id": 2, "action": "merge", "target_id": 1},
            {"id": 3, "action": "keep",
             "summary": "Editor 發布安全修補",
             "event_type": "security_fix", "entities": ["Editor"]},
        ]}

    def test_local_id_mapping_restores_original_ids_and_links(self):
        with patch("src.editorial_digest._request_parsed_ai",
                   return_value=self.good()) as ai:
            result = audit_events(self.rows, [], {"calls": 0, "latencies": []})
        self.assertEqual([row["id"] for row in result], [5, 48])
        self.assertEqual(result[0]["related_urls"],
                         ["https://example.org/a", "https://example.org/b"])
        incoming = json.loads(ai.call_args.args[0][1]["content"])
        self.assertEqual([row["id"] for row in incoming["candidates"]],
                         [1, 2, 3])
        self.assertNotIn("27", json.dumps(incoming["candidates"]))

    def test_malformed_local_ids_are_repaired_by_ai_retry(self):
        wrong = {"decisions": [
            {"id": 1, "action": "keep", "summary": "事件一",
             "event_type": "update", "entities": []},
            {"id": 27, "action": "historical_duplicate"},
        ]}
        with patch("src.editorial_digest._request_parsed_ai",
                   side_effect=[wrong, self.good()]) as ai:
            result = audit_events(self.rows, [], {"calls": 0, "latencies": []})
        self.assertEqual([row["id"] for row in result], [5, 48])
        self.assertEqual(ai.call_count, 2)
        repair_prompt = ai.call_args.args[0][-1]["content"]
        self.assertIn("missing_ids", repair_prompt)
        self.assertIn("unexpected_ids", repair_prompt)

    def test_invalid_merge_target_retried_then_rejected(self):
        wrong = {"decisions": [
            {"id": 1, "action": "keep", "summary": "事件一",
             "event_type": "update", "entities": []},
            {"id": 2, "action": "merge", "target_id": 99},
            {"id": 3, "action": "historical_duplicate"},
        ]}
        with patch("src.editorial_digest._request_parsed_ai",
                   return_value=wrong) as ai:
            with self.assertRaisesRegex(ValueError, "invalid merge target"):
                audit_events(self.rows, [], {"calls": 0, "latencies": []})
        self.assertEqual(ai.call_count, 3)

    def test_historical_duplicate_does_not_remove_unrelated_story(self):
        answer = {"decisions": [
            {"id": 1, "action": "historical_duplicate"},
            {"id": 2, "action": "keep", "summary": "獨立產品發布",
             "event_type": "launch", "entities": []},
            {"id": 3, "action": "keep", "summary": "安全修補",
             "event_type": "security_fix", "entities": []},
        ]}
        with patch("src.editorial_digest._request_parsed_ai",
                   return_value=answer):
            output = audit_events(self.rows, [], {"calls": 0, "latencies": []})
        self.assertEqual([row["id"] for row in output], [27, 48])


if __name__ == "__main__":
    unittest.main()
