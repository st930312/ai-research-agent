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
        answer = '{"groups":[{"ids":[1,2,3],"keep":2},{"ids":[4],"keep":4}],"historical_duplicates":[]}'
        with patch("src.editorial_digest._request_ai", return_value=answer):
            chosen = audit_events(self.items, [], {"calls": 0, "latencies": []})
        self.assertEqual([row["id"] for row in chosen], [2, 4])

    def test_rejects_news_already_in_neon_history(self):
        answer = '{"groups":[{"ids":[4],"keep":4}],"historical_duplicates":[1,2,3]}'
        history = [{"title": "Nvidia investigates Jensen Huang", "category": "tech"}]
        with patch("src.editorial_digest._request_ai", return_value=answer) as request:
            chosen = audit_events(self.items, history, {"calls": 0, "latencies": []})
        self.assertEqual([row["id"] for row in chosen], [4])
        self.assertIn("Nvidia investigates Jensen Huang", request.call_args.args[0][1]["content"])

    def test_fail_closed_when_audit_omits_a_selected_article(self):
        answer = '{"groups":[{"ids":[1,2],"keep":1}],"historical_duplicates":[]}'
        with patch("src.editorial_digest._request_ai", return_value=answer):
            with self.assertRaisesRegex(ValueError, "omitted"):
                audit_events(self.items, [], {"calls": 0, "latencies": []})

    def test_fail_closed_when_same_id_repeated(self):
        answer = '{"groups":[{"ids":[1,2],"keep":1},{"ids":[2,3,4],"keep":3}],"historical_duplicates":[]}'
        with patch("src.editorial_digest._request_ai", return_value=answer):
            with self.assertRaisesRegex(ValueError, "duplicated"):
                audit_events(self.items, [], {"calls": 0, "latencies": []})

    def test_unrelated_updates_from_same_company_can_survive(self):
        answer = '{"groups":[{"ids":[1],"keep":1},{"ids":[2],"keep":2},{"ids":[3],"keep":3},{"ids":[4],"keep":4}],"historical_duplicates":[]}'
        with patch("src.editorial_digest._request_ai", return_value=answer):
            chosen = audit_events(self.items, [], {"calls": 0, "latencies": []})
        self.assertEqual(len(chosen), 4)


if __name__ == "__main__":
    unittest.main()
