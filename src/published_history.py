"""Neon PostgreSQL record of successfully published news, without repo commits."""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from urllib.parse import urlsplit

from .core import canonical_url

SCHEMA = """
CREATE TABLE IF NOT EXISTS published_events (
 event_key TEXT PRIMARY KEY,
 url TEXT NOT NULL,
 title TEXT NOT NULL,
 category TEXT NOT NULL,
 source TEXT NOT NULL,
 repo TEXT,
 published_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS published_events_time ON published_events (published_at DESC);
CREATE INDEX IF NOT EXISTS published_events_repo ON published_events (repo, published_at DESC);
"""

def repo_name(row):
    if row.get("source") not in ("github_search", "github_release"):
        return None
    parts = [p for p in urlsplit(row.get("url") or "").path.split("/") if p]
    return "/".join(parts[:2]).lower() if len(parts) >= 2 else None

def event_key(row):
    return hashlib.sha256(canonical_url(row.get("url") or "").encode("utf-8")).hexdigest()

def normalized_title(title):
    title = re.sub(r"[^\w\u4e00-\u9fff]+", " ", (title or "").lower())
    return " ".join(title.split())

def filter_published(candidates, history):
    """Filter exact links, same recent GitHub repo, highly similar old titles."""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    urls = {h["event_key"] for h in history}
    titles = [normalized_title(h.get("title")) for h in history]
    blocked_repos = set()
    for h in history:
        if h.get("repo") and h.get("source") == "github_search":
            when = h.get("published_at")
            if when is None or now - when < timedelta(days=90):
                blocked_repos.add(h["repo"])
    kept, skipped = [], 0
    for row in candidates:
        title = normalized_title(row.get("title"))
        repo = repo_name(row)
        duplicate = (
            event_key(row) in urls
            or (row.get("source") == "github_search" and repo in blocked_repos)
            or (bool(title) and any(
                SequenceMatcher(None, title, prior).ratio() >= 0.88
                for prior in titles if prior
            ))
        )
        if duplicate:
            skipped += 1
        else:
            kept.append(row)
    return kept, skipped

class PublishedHistory:
    def __init__(self, url=None):
        self.url = url or os.getenv("DATABASE_URL")
        if not self.url:
            raise RuntimeError("Missing DATABASE_URL; configure Neon Actions Secret")
        if not self.url.startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL URI")

    def connect(self):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("Missing psycopg; install requirements.txt") from exc
        return psycopg.connect(self.url, sslmode="require", connect_timeout=12)

    def setup_and_probe(self):
        with self.connect() as conn:
            with conn.cursor() as cur:
                for statement in SCHEMA.split(";"):
                    if statement.strip():
                        cur.execute(statement)
                cur.execute("SELECT 1")
                assert cur.fetchone()[0] == 1

    def recent(self, days=90):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT event_key, url, title, category, source, repo, published_at "
                    "FROM published_events WHERE published_at >= NOW() - (%s * INTERVAL '1 day') "
                    "ORDER BY published_at DESC LIMIT 2500", (days,)
                )
                columns = [col.name for col in cur.description]
                return [dict(zip(columns, values)) for values in cur.fetchall()]

    def mark_sent(self, articles):
        if not articles:
            return 0
        with self.connect() as conn:
            with conn.cursor() as cur:
                for row in articles:
                    cur.execute(
                        "INSERT INTO published_events (event_key, url, title, category, source, repo) "
                        "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (event_key) DO NOTHING",
                        (event_key(row), canonical_url(row["url"]), row.get("title") or "",
                         row.get("category") or "", row.get("source") or "", repo_name(row))
                    )
        return len(articles)

def smoke_test():
    """Prove SELECT, DDL and transactional DML; leave no test story behind."""
    db = PublishedHistory()
    db.setup_and_probe()
    with db.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SAVEPOINT smoke")
            cur.execute(
                "INSERT INTO published_events (event_key,url,title,category,source) "
                "VALUES ('__smoke_test__','https://example.org/','Test','test','smoke') "
                "ON CONFLICT (event_key) DO NOTHING"
            )
            cur.execute("ROLLBACK TO SAVEPOINT smoke")
    print("NEON_SMOKE=OK (schema, select, insert, rollback)", flush=True)

if __name__ == "__main__":
    smoke_test()
