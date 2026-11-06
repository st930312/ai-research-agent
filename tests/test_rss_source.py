import unittest
from src.rss_source import parse_feed

class RSSTests(unittest.TestCase):
    def test_rss_items(self):
        data = b"""<rss><channel><item><title>New GPU chip</title>
        <link>https://example.com/chip</link><description>New &amp; fast</description>
        <pubDate>Fri, 06 Nov 2026 08:00:00 GMT</pubDate>
        </item></channel></rss>"""
        rows = parse_feed(data, "Tech News", "tech")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["suggested_category"], "tech")
        self.assertEqual(rows[0]["description"], "New & fast")

    def test_atom_items(self):
        data = b"""<feed xmlns="http://www.w3.org/2005/Atom">
        <entry><title>AI release</title><link href="https://example.com/ai" />
        <updated>2026-11-06T00:00:00Z</updated></entry></feed>"""
        rows = parse_feed(data, "AI Feed", "ai")
        self.assertEqual(rows[0]["url"], "https://example.com/ai")

    def test_skip_insecure_url(self):
        data = b"""<rss><channel><item><title>Bad link</title>
        <link>http://example.com</link></item></channel></rss>"""
        self.assertEqual(parse_feed(data, "Test", "tech"), [])

if __name__ == "__main__":
    unittest.main()
