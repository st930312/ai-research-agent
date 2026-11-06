import unittest
from src.core import canonical_url, dedup, hn_search, searx_search


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


if __name__ == '__main__':
    unittest.main()
