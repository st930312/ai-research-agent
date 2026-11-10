"""Regression checks for reliability, quantitative claim validation and format."""
import unittest
from unittest.mock import Mock, patch
from src.fact_guard import numeric_claims, validate_source_grounding
from src.publication import digest_key, PublicationLedger
from src.wide_discord import send_wide_messages
from src.published_history import SCHEMA


class FactGuardTests(unittest.TestCase):
    def test_normalizes_percentage_spacing(self):
        self.assertEqual(numeric_claims("成長 12 %，降幅 3.5％"), {"12%", "3.5%"})

    def test_unsupported_claim_fails(self):
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_NUMERIC_CLAIM"):
            validate_source_grounding(
                "營收成長 37%", {"title": "Revenue report", "description": "Revenue grew 7%"}
            )

    def test_source_supports_number(self):
        self.assertTrue(validate_source_grounding(
            "營收成長 37%", {"title": "Revenue report", "body_excerpt": "Revenue grew 37%"}
        ))

    def test_roundup_source_supports_number(self):
        self.assertTrue(validate_source_grounding(
            "產業報導提及 12 億美元",
            {"title": "Industry news", "roundup_sources": [
                {"title": "Another event", "body_excerpt": "Investment: 12億美元"}]}
        ))


class PublicationTests(unittest.TestCase):
    def test_digest_fingerprint_stable(self):
        self.assertEqual(digest_key(["a", "b"]), digest_key(["a", "b"]))
        self.assertNotEqual(digest_key(["a", "b"]), digest_key(["b", "a"]))

    def test_publication_tables_present(self):
        self.assertIn("publication_messages", SCHEMA)
        self.assertIn("publication_events", SCHEMA)
        self.assertIn("pipeline_runs", SCHEMA)

    @patch("src.wide_discord.time.sleep")
    @patch("src.wide_discord.urllib.request.urlopen")
    def test_message_acknowledged_after_webhook_success(self, http, _sleep):
        http.return_value.__enter__.return_value.status = 204
        ledger = Mock()
        ledger.claim.return_value = True
        with patch.dict("os.environ", {"DISCORD_WEBHOOK_URL":
                                     "https://discord.com/api/webhooks/123/token"}):
            send_wide_messages(["first", "second"], ledger=ledger)
        self.assertEqual(ledger.claim.call_count, 2)
        self.assertEqual(ledger.sent.call_count, 2)

    @patch("src.wide_discord.time.sleep")
    @patch("src.wide_discord.urllib.request.urlopen")
    def test_failed_webhook_never_marks_sent(self, http, _sleep):
        http.side_effect = OSError("network uncertain")
        ledger = Mock()
        ledger.claim.return_value = True
        with patch.dict("os.environ", {"DISCORD_WEBHOOK_URL":
                                     "https://discord.com/api/webhooks/123/token"}):
            with self.assertRaises(OSError):
                send_wide_messages(["first"], ledger=ledger)
        ledger.sent.assert_not_called()


if __name__ == "__main__":
    unittest.main()
