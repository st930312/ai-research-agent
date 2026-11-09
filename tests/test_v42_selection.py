import unittest
from unittest.mock import patch
from datetime import datetime,timezone
from src.editorial_digest import shortlist,cap_selection
from src.rss_source import rss_discover,FEEDS
from src.github_source import github_discover

class V42SelectionTests(unittest.TestCase):
    def test_source_coverage(self):
        self.assertGreaterEqual(len(FEEDS["gaming"]),3)
        self.assertTrue(any("semiengineering" in url for _,url in FEEDS["finance"]))

    def test_gaming_feed_has_no_keyword_filter(self):
        data=b"""<rss><channel><item>
        <title>Astral Tide: Echoes chapter expansion</title>
        <link>https://example.org/astral</link>
        <pubDate>Mon, 09 Nov 2026 09:00:00 GMT</pubDate>
        </item></channel></rss>"""
        with patch.dict("src.rss_source.FEEDS",
                        {"gaming":[("Gematsu","https://example.org/feed")]}):
            rows,_=rss_discover(limit=5,fetcher=lambda _:data)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["suggested_category"],"gaming")

    def test_search_new_and_established_github(self):
        seen=[]
        def fake(url):
            seen.append(url)
            return {"items":[{"html_url":"https://github.com/test/established",
                "full_name":"test/established","created_at":"2020-01-01T00:00:00Z",
                "pushed_at":datetime.now(timezone.utc).isoformat(),
                "stargazers_count":980,"description":"Popular useful tool"}]}
        rows=github_discover("dev",limit=3,fetcher=fake)
        self.assertTrue(any("pushed%3A" in url for url in seen))
        self.assertTrue(any("created%3A" in url for url in seen))
        self.assertEqual(rows[0]["url"],"https://github.com/test/established")

    def test_ai_selects_game_without_restricted_keywords(self):
        row={"id":1,"title":"Silver Arcadia chapter update",
             "url":"https://example.org/g", "source":"rss",
             "suggested_category":"gaming","publisher":"Gematsu",
             "published_at":datetime.now(timezone.utc).isoformat()}
        with patch("src.editorial_digest._request_ai",return_value=
                   '{"selected":[{"id":1,"category":"gaming","importance":3}]}'):
            picks=shortlist([row],{"calls":0,"latencies":[]})
        self.assertEqual(len(cap_selection(picks)),1)

if __name__=="__main__":
    unittest.main()
