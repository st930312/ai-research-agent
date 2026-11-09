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
    "dev": [
        ("Ars Technica Technology Lab", "https://feeds.arstechnica.com/arstechnica/technology-lab"),
        ("The Register DevOps", "https://api.theregister.com/api/v1/article?limit=25&orderBy=published&query=tag%3Adevops&remapper=rss&site_id=2"),
    ],
    "tech": [
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Ars Technica Science", "https://feeds.arstechnica.com/arstechnica/science"),
    ],
    "gaming": [
        ("巴哈姆特 GNN", "https://gnn.gamer.com.tw/rss.xml"),
    ],
    "finance": [
        ("TechCrunch Fintech", "https://techcrunch.com/category/fintech/feed/"),
    ],
    "tw_stock": [
        ("Yahoo 股市 台股動態", "https://tw.stock.yahoo.com/rss?category=tw-market"),
        ("中央社 產經證券", "https://feeds.feedburner.com/rsscna/finance"),
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
                rows = parse_feed(fetcher(url), label, category,
                                  max(limit * 4, 20) if category in ("gaming", "tw_stock") else limit)
                if category == "gaming":
                    # Favor Steam/PC games and major game releases over anime notices.
                    relevant = re.compile(
                        r"Steam|PC|電腦|遊戲|發售|上市|開發|新作|主機|Xbox|Switch|PS[45]|獨立", re.I
                    )
                    preferred = re.compile(r"Steam|PC|電腦|獨立遊戲", re.I)
                    rows = [row for row in rows if relevant.search(row["title"])]
                    rows.sort(key=lambda row: (row.get("published_at") or "", bool(preferred.search(row["title"]))), reverse=True)
                if category == "tw_stock":
                    # All industries qualify, not only technology / AI.
                    equity = re.compile(
                        r"台股|台積|股票|股市|股價|股利|股息|上市|上櫃|櫃買|"
                        r"大盤|加權|指數|外資|投信|法人|三大法人|融資|融券|"
                        r"成交量|成交值|漲停|跌停|殖利率|ETF|個股|盤中|盤後|"
                        r"金控|銀行股|航運股|營建股|傳產股|金融股|電子股|"
                        r"營收|法說|財報|台灣證交所|證交所|櫃買中心", re.I
                    )
                    rows = [row for row in rows if
                            label.startswith("Yahoo") or
                            equity.search(row["title"] + " " + row.get("description", ""))]
                    rows.sort(key=lambda row: row.get("published_at") or "", reverse=True)
                rows = rows[:max(limit, 12) if category == "gaming" else
                             max(limit, 10) if category == "tw_stock" else limit]
                results.extend(rows)
                counts[label] = len(rows)
            except Exception as exc:
                counts[label] = 0
                print(f"RSS_WARN {label}: {type(exc).__name__}", flush=True)
    return results, counts
