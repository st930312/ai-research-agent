"""Source provenance rules for international finance, not title keyword gates."""
from urllib.parse import urlsplit

INDUSTRY_PUBLISHERS = frozenset({
    "TechCrunch Fintech", "Semiconductor Engineering", "SemiWiki",
})
BLOCKED_HOSTS = frozenset({
    "github.com", "www.github.com", "youtube.com",
    "www.youtube.com", "youtu.be",
})

def industry_eligible(row):
    """Trusted specialist provenance; relevance is decided by shared AI."""
    host = (urlsplit(row.get("url") or "").hostname or "").lower()
    if host in BLOCKED_HOSTS or row.get("source") in ("github_search", "github_release"):
        return False
    if row.get("source") == "rss" and row.get("publisher") in INDUSTRY_PUBLISHERS:
        return True
    return row.get("source") == "hackernews" and row.get("suggested_category") == "finance"

def gaming_eligible(row):
    """Source category only; game importance is always decided by shared AI."""
    return row.get("suggested_category") == "gaming"
