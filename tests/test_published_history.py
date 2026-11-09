import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from src.published_history import (
    event_key, repo_name, release_tag, filter_published, PublishedHistory, normalized_title, SCHEMA
)

class NeonHistoryTests(unittest.TestCase):
    def test_url_fingerprint_strips_tracking(self):
        first = {"url": "https://example.org/news?utm_source=feed"}
        second = {"url": "https://example.org/news"}
        self.assertEqual(event_key(first), event_key(second))

    def test_legacy_raw_url_hash_does_not_repeat_published_story(self):
        import hashlib
        old_url = "https://techcrunch.com/2026/11/08/nvidia-news/"
        legacy_hash = hashlib.sha256(old_url.encode("utf-8")).hexdigest()
        history = [{
            "url": old_url, "event_key": legacy_hash,
            "title": "Published Nvidia investigation", "category": "tech",
            "source": "rss", "repo": None,
            "published_at": datetime.now(timezone.utc),
        }]
        candidate = {
            "url": "https://techcrunch.com/2026/11/08/nvidia-news/?utm_source=rss",
            "title": "Nvidia story with a different classification",
            "suggested_category": "ai", "source": "rss",
        }
        kept, skipped = filter_published([candidate], history)
        self.assertEqual(kept, [])
        self.assertEqual(skipped, 1)

    def test_previous_github_repo_blocked_but_new_release_not(self):
        old = {"event_key": "previous", "title": "Different original title",
               "source": "github_search", "repo": "owner/project",
               "published_at": datetime.now(timezone.utc)}
        rows = [
            {"url": "https://github.com/owner/project", "title": "Fresh description",
             "source": "github_search"},
            {"url": "https://github.com/owner/project/releases/tag/v2.0", "title": "v2.0 released",
             "source": "github_release"},
        ]
        kept, skipped = filter_published(rows, [old])
        self.assertEqual(skipped, 1)
        self.assertEqual(kept[0]["source"], "github_release")

    def test_same_story_different_urls_filtered(self):
        old = {"event_key": "old", "title": "Major cloud service outage",
               "source": "rss", "repo": None,
               "published_at": datetime.now(timezone.utc)}
        rows = [
            {"url": "https://another.example.org/story", "title": "Major cloud service outage",
             "source": "rss"}
        ]
        self.assertEqual(filter_published(rows, [old])[1], 1)

    def test_new_important_release_same_repo_is_not_preemptively_removed(self):
        old = {"event_key": "old-release", "title": "owner/project — v1.0",
               "source": "github_release", "repo": "owner/project",
               "release_tag": "v1.0", "category": "dev",
               "published_at": datetime.now(timezone.utc)}
        new = {"url": "https://github.com/owner/project/releases/tag/v2.0",
               "title": "owner/project — v2.0", "tag": "v2.0",
               "source": "github_release", "suggested_category": "dev"}
        self.assertEqual(filter_published([new], [old])[1], 0)
        self.assertEqual(release_tag(new), "v2.0")

    def test_same_release_different_url_still_filtered(self):
        old = {"event_key": "old-release", "title": "owner/project — v2.0",
               "source": "github_release", "repo": "owner/project",
               "release_tag": "v2.0", "category": "dev",
               "published_at": datetime.now(timezone.utc)}
        row = {"url": "https://github.com/owner/project/releases/tag/v2.0?foo=bar",
               "title": "Critical owner project release", "source": "github_release",
               "suggested_category": "dev"}
        self.assertEqual(filter_published([row], [old])[1], 1)

    def test_same_repo_stars_alone_is_not_a_major_update(self):
        old = {"event_key": "old-repo", "title": "owner/project",
               "source": "github_search", "repo": "owner/project",
               "published_at": datetime.now(timezone.utc)}
        row = {"url": "https://github.com/owner/project", "title": "owner/project new stars",
               "source": "github_search", "score": 50000}
        self.assertEqual(filter_published([row], [old])[1], 1)

    def test_schema_persists_event_evidence_and_release_identity(self):
        for col in ("event_summary", "article_summary", "event_entities",
                    "event_type", "release_tag", "source_urls"):
            self.assertIn(col, SCHEMA)

    def test_tracking_previously_published_repo_discovers_later_release(self):
        from src.editorial_digest import main
        latest = datetime.now(timezone.utc).isoformat()
        historical = {"event_key": "old", "title": "owner/project",
                      "category": "github", "source": "github_search",
                      "repo": "owner/project", "published_at": datetime.now(timezone.utc)}
        release = {"title": "owner/project v2.0", "source": "github_release",
                   "url": "https://github.com/owner/project/releases/tag/v2.0",
                   "published_at": latest, "suggested_category": "dev", "tag": "v2.0"}
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://example",
                                       "ENABLE_REAL_AI": "false"}, clear=True), \
             patch("src.editorial_digest.collect_candidates", return_value=([], {})), \
             patch("src.editorial_digest.PublishedHistory") as db, \
             patch("src.editorial_digest.github_releases", return_value=([release], {})) as releases:
            db.return_value.recent.return_value = [historical]
            main()
            releases.assert_called_once_with(limit=12, repos=["owner/project"])

    def test_no_credentials_does_not_leak_or_connect(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "DATABASE_URL"):
                PublishedHistory()

    def test_repo_name(self):
        self.assertEqual(repo_name({"source": "github_search", "url": "https://github.com/A/B"}), "a/b")
        self.assertIsNone(repo_name({"source": "rss", "url": "https://example.com/a"}))
