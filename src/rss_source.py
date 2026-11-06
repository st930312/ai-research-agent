"""Public RSS metadata reader for recent technology / industry news."""
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FEEDS = {
    "ai": [
        ("Ars Technica AI", "https://arstechnica.com/ai/feed/"),
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ],
    "tech": [
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Ars Technica Science", "https://feeds.arstechnica.com/arstechnica/science"),
    ],
    "finance": [
        ("TechCrunch Fintech", "https://techcrunch.com/category/fintech/feed/"),
    ],
}
UA = "AIResearchAgent/0.6 (RSS digest reader)"

def fetch_rss(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml,application/atom+xml,application/xml"})
    with urllib.request.urlopen(req, timeout=18) as response:
        xml = response.read(600_001)
        if len(xml) > 600_000:
            raise ValueError("RSS feed too large")
        return xml

def _plain(text):
    text = re.sub(r"<[^>]*>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()

def _date(text):
    if not text:
        return None
    try:
        value = parsedate_to_datetime(text)
    except (ValueError, TypeError):
        try:
            value = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()

def parse_feed(data, label, category, limit=6):
    root = ET.fromstring(data)
    rows = []
    if root.tag.endswith("feed"):
        ns = "{http://www.w3.org/2005/Atom}"
        for entry in root.findall(ns + "entry")[:limit]:
            link = ""
            for candidate in entry.findall(ns + "link"):
                if candidate.attrib.get("rel", "alternate") == "alternate":
                    link = candidate.attrib.get("href", "")
                    break
            rows.append({
                "title": _plain(entry.findtext(ns + "title")),
                "url": link,
                "description": _plain(entry.findtext(ns + "summary") or entry.findtext(ns + "content"))[:320],
                "published_at": _date(entry.findtext(ns + "published") or entry.findtext(ns + "updated")),
            })
    else:
        for item in root.findall(".//channel/item")[:limit]:
            rows.append({
                "title": _plain(item.findtext("title")),
                "url": item.findtext("link") or "",
                "description": _plain(item.findtext("description"))[:320],
                "published_at": _date(item.findtext("pubDate")),
            })
    return [{
        **row, "source": "rss", "publisher": label, "suggested_category": category
    } for row in rows if row.get("title") and row.get("url", "").startswith("https://")]

def rss_discover(limit=5, fetcher=fetch_rss):
    results = []
    counts = {}
    for category, feeds in FEEDS.items():
        for label, url in feeds:
            try:
                rows = parse_feed(fetcher(url), label, category, limit)
                results.extend(rows)
                counts[label] = len(rows)
            except Exception as exc:
                counts[label] = 0
                print(f"RSS_WARN {label}: {type(exc).__name__}", flush=True)
    return results, counts
