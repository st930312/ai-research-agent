"""Curated GitHub Release discovery and lightweight event-aware deduplication."""
from __future__ import annotations
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from difflib import SequenceMatcher

TRACKED_REPOS = (
    "golang/go", "facebook/react", "moby/moby", "redis/redis",
    "docker/compose", "kubernetes/kubernetes",
)
IGNORED_RELEASE = re.compile(r"(?i)(alpha|beta|nightly|snapshot|preview|rc[.-]?\d|canary)")

def fetch_release_json(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "AIResearchAgent/0.7"}
    if os.getenv("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=15) as response:
        return json.load(response)

def github_releases(limit=6, fetcher=fetch_release_json):
    """Track noteworthy stable releases from a small explicit allowlist."""
    results = []
    counts = {}
    for full_name in TRACKED_REPOS:
        try:
            data = fetcher(f"https://api.github.com/repos/{full_name}/releases?per_page=2")
            rows = []
            for release in data if isinstance(data, list) else []:
                tag = str(release.get("tag_name") or "")
                if release.get("draft") or release.get("prerelease") or IGNORED_RELEASE.search(tag):
                    continue
                url = release.get("html_url") or ""
                if not url.startswith(f"https://github.com/{full_name}/releases/tag/"):
                    continue
                rows.append({
                    "title": f"{full_name} — {release.get('name') or tag}",
                    "url": url, "source": "github_release",
                    "description": (release.get("body") or "")[:700],
                    "body_excerpt": (release.get("body") or "")[:5000],
                    "published_at": release.get("published_at"),
                    "suggested_category": "dev",
                    "repo": full_name, "tag": tag,
                })
            counts[full_name] = len(rows)
            results.extend(rows)
        except Exception as exc:
            counts[full_name] = 0
            print(f"RELEASE_WARN {full_name}: {type(exc).__name__}", flush=True)
    return results[:limit], counts

def norm_title(title):
    title = re.sub(r"(?i)\b(the|a|an|new|latest|announces|announced|launches|released)\b", " ", title or "")
    title = re.sub(r"[^\w\u4e00-\u9fff]+", " ", title.lower())
    return " ".join(title.split())

def event_dedup(rows, ratio=0.88):
    """Conservative near-duplicate titles + canonical URL dedup; avoid over-merging news."""
    output, urls, titles = [], set(), []
    for row in rows:
        url = row.get("url", "")
        parsed = urllib.parse.urlsplit(url)
        canon = (parsed.netloc.lower(), parsed.path.rstrip("/").lower())
        title = norm_title(row.get("title") or "")
        if not title or canon in urls:
            continue
        if any(SequenceMatcher(None, title, seen).ratio() >= ratio for seen in titles):
            continue
        output.append(row)
        urls.add(canon)
        titles.append(title)
    return output
