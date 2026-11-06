import unittest
from src.core import canonical_url, dedup, hn_search, searx_search
from src.github_source import github_discover


class CoreTests(unittest.TestCase):
    def test_canonical(self):
        self.assertEqual(
            canonical_url('https://Example.org/a/?utm_source=abc&x=2#top'),
            'https://example.org/a?x=2'
        )

    def test_dedup(self):
        rows = [{'url': 'https://example.org/a?utm_source=x'},
                {'url': 'https://example.org/a'}]
        self.assertEqual(len(dedup(rows)), 1)

    def test_hn(self):
        rows = hn_search('LLM', fetcher=lambda _: {
            'hits': [{'title': 'Hello', 'url': 'https://example.com',
                      'created_at': '2026-11-06', 'points': 2}]
        })
        self.assertEqual(rows[0]['source'], 'hackernews')

    def test_searx(self):
        rows = searx_search('https://example.net', 'LLM', fetcher=lambda _: {
            'results': [{'title': 'Hello', 'url': 'https://example.com', 'content': 'Text'}]
        })
        self.assertEqual(len(rows), 1)

    def test_searx_https(self):
        with self.assertRaises(ValueError):
            searx_search('http://example.net', 'LLM')

    def test_github_discover(self):
        def mock_fetch(url):
            return {"items": [{
                "full_name": "example/agent",
                "html_url": "https://github.com/example/agent",
                "description": "An example agent",
                "created_at": "2026-11-05T00:00:00Z",
                "stargazers_count": 12,
                "language": "Python",
            }]}
        rows = github_discover("ai", limit=5, fetcher=mock_fetch)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "github_search")
        self.assertEqual(rows[0]["score"], 12)


if __name__ == '__main__':
    unittest.main()
