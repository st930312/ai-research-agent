import unittest
from src.content_enrichment import readable_html, enrich, MAX_TEXT

class EnrichmentTests(unittest.TestCase):
    def test_html_extracts_body_and_excludes_script(self):
        doc = '<html><body><nav>MENU</nav><article><h1>Headline</h1><p>Useful research detail</p><script>secret junk</script></article></body></html>'
        result = readable_html(doc)
        self.assertIn("Useful research detail", result)
        self.assertNotIn("secret junk", result)

    def test_github_readme(self):
        row = {"title": "org/repo", "url": "https://github.com/org/repo", "source": "github_search"}
        def fetcher(url, headers=None):
            self.assertEqual(url, "https://api.github.com/repos/org/repo/readme")
            return ("# Sample\nDetailed README", "text/plain")
        result = enrich(row, fetcher=fetcher)
        self.assertEqual(result["body_status"], "ok")
        self.assertEqual(result["body_kind"], "github_readme")
        self.assertIn("Detailed README", result["body_excerpt"])

    def test_unavailable_does_not_break_run(self):
        row = {"url": "https://example.com/doc", "source": "hackernews"}
        def fetcher(url, headers=None):
            raise TimeoutError("test")
        result = enrich(row, fetcher=fetcher)
        self.assertEqual(result["body_status"], "unavailable:TimeoutError")
        self.assertEqual(result["body_excerpt"], "")

    def test_bounded_length(self):
        text = "<article><p>" + "X"*15000 + "</p></article>"
        self.assertLessEqual(len(readable_html(text)), MAX_TEXT)

if __name__ == "__main__":
    unittest.main()
