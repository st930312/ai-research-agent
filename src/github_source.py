"""GitHub discovery via documented REST search (trending-like, not official Trending)."""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

QUERIES = {
    "ai": "topic:llm OR topic:ai-agent",
    "dev": "topic:developer-tools",
    "tech": "topic:technology",
    "finance": "topic:fintech",
}
# GitHub's search grammar has special behavior for OR; use independent queries.
TOPIC_TERMS = {
    "ai": ["topic:llm", "topic:ai-agent"],
    "dev": ["topic:developer-tools", "topic:cli"],
    "tech": ["topic:technology", "topic:hardware"],
    "finance": ["topic:fintech", "topic:quantitative-finance"],
}

def github_discover(topic="ai", limit=5, fetcher=None):
    if topic not in TOPIC_TERMS:
        raise ValueError("unknown topic")
    if fetcher is None:
        fetcher = _fetch
    since = (datetime.now(timezone.utc) - timedelta(days=14)).date().isoformat()
    recently_pushed = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
    entries = []
    searches = [
        (term, f"created:>={since} stars:>=2", "stars")
        for term in TOPIC_TERMS[topic]
    ]
    # Catch established projects with genuine recent work, alongside new ones.
    searches.append((TOPIC_TERMS[topic][0],
                     f"pushed:>={recently_pushed} stars:>=50", "updated"))
    for term, window, sort in searches:
        query = urllib.parse.urlencode({
            "q": f"{term} {window}",
            "sort": sort, "order": "desc", "per_page": limit,
        })
        data = fetcher("https://api.github.com/search/repositories?" + query)
        for item in data.get("items", [])[:limit]:
            url = item.get("html_url", "")
            if not url.startswith("https://github.com/"):
                continue
            entries.append({
                "title": item.get("full_name", ""),
                "url": url, "source": "github_search",
                "description": (item.get("description") or "")[:400],
                "published_at": item.get("created_at"),
                "last_pushed_at": item.get("pushed_at"),
                "score": item.get("stargazers_count", 0),
                "language": item.get("language"),
                "note": "Recently created or recently active project; NOT official Trending.",
            })
    # A small bounded discovery search; GitHub rate limits handled upstream.
    seen = set()
    result = []
    for item in sorted(entries, key=lambda x: x["score"], reverse=True):
        if item["url"] not in seen:
            seen.add(item["url"])
            result.append(item)
    return result[:limit]

def _fetch(url):
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "ai-research-agent/0.2"}
    token = os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as res:
        return json.load(res)
