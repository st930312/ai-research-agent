import unittest
from unittest.mock import patch

from src.tech_digest import create_prompt, discord_chunks, send_discord

class DigestTests(unittest.TestCase):
    def test_prompt_has_source_url_and_excerpt(self):
        items = [{"title": "Example", "url": "https://example.org/a", "source": "hackernews",
                  "body_status": "ok", "body_excerpt": "Long story body"}]
        system, user = create_prompt(items, "ai")
        self.assertIn("繁體中文", system)
        self.assertIn("https://example.org/a", user)
        self.assertIn("Long story body", user)

    def test_discord_chunks_fit(self):
        long_content = "A" * 4500
        chunks = discord_chunks(long_content)
        self.assertTrue(all(0 < len(chunk) <= 1800 for chunk in chunks))
        self.assertEqual("".join(chunks), long_content)

    def test_discord_requires_explicit_webhook(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError):
                send_discord("test")

    def test_discord_rejects_non_discord_host(self):
        with patch.dict("os.environ", {"DISCORD_WEBHOOK_URL": "https://example.com/webhook"}):
            with self.assertRaises(ValueError):
                send_discord("test")

if __name__ == "__main__":
    unittest.main()
