"""Bounded public-page article and GitHub README enrichment, no LLM calls."""
from __future__ import annotations

import html
import base64
import ipaddress
import json
import os
import re
import socket
import urllib.parse
import urllib.request
from html.parser import HTMLParser

MAX_BYTES = 250_000
MAX_TEXT = 5_000
USER_AGENT = "AIResearchAgent/0.3 (public research; respectful crawl limits)"
BLOCK_TAGS = {"script", "style", "nav", "footer", "header", "aside", "form", "svg", "noscript"}
ARTICLE_TAGS = {"article", "main"}

class ReadableText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.article_depth = 0
        self.parts = []
        self.fallback_parts = []
    def handle_starttag(self, tag, attrs):
        if tag in BLOCK_TAGS:
            self.depth += 1
        if tag in ARTICLE_TAGS:
            self.article_depth += 1
        if tag in {"p", "h1", "h2", "h3", "li", "blockquote"} and self.depth == 0:
            (self.parts if self.article_depth else self.fallback_parts).append("\n")
    def handle_endtag(self, tag):
        if tag in BLOCK_TAGS and self.depth > 0:
            self.depth -= 1
        if tag in ARTICLE_TAGS and self.article_depth > 0:
            self.article_depth -= 1
    def handle_data(self, data):
        if self.depth == 0 and data.strip():
            (self.parts if self.article_depth else self.fallback_parts).append(data + " ")

def readable_html(text):
    parser = ReadableText()
    parser.feed(text)
    selected = "".join(parser.parts)
    if len(selected.strip()) < 180:
        selected = selected + "\n" + "".join(parser.fallback_parts)
    return re.sub(r"\s+", " ", html.unescape(selected)).strip()[:MAX_TEXT]

def assert_public_https(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise ValueError("Only public HTTPS URLs may be fetched")
    host = p.hostname
    if host.lower() in {"localhost", "localhost.localdomain"}:
        raise ValueError("Local host not allowed")
    for record in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
        address = ipaddress.ip_address(record[4][0])
        if not address.is_global:
            raise ValueError("Non-public network address not allowed")
    return url

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Redirects require a new security check; deny them in the smoke test.
        return None

def get_public_content(url, headers=None):
    assert_public_https(url)
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html, text/plain, application/vnd.github.raw+json",
        **(headers or {}),
    })
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(req, timeout=12) as response:
        ctype = response.headers.get("Content-Type", "").lower()
        if not any(x in ctype for x in ("text/html", "text/plain", "text/markdown", "application/octet-stream", "application/json")):
            raise ValueError("Unsupported content type")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Document is too large")
    return raw.decode("utf-8", errors="replace"), ctype

def enrich(item, fetcher=get_public_content):
    item = dict(item)
    url = item.get("url") or ""
    try:
        if item.get("source") == "github_search":
            p = urllib.parse.urlsplit(url)
            if p.hostname != "github.com":
                raise ValueError("Not a GitHub repository")
            parts = p.path.strip("/").split("/")
            if len(parts) != 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", v) for v in parts):
                raise ValueError("Invalid repository path")
            api_url = "https://api.github.com/repos/" + "/".join(parts) + "/readme"
            auth = {}
            if os.getenv("GH_TOKEN"):
                auth["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
            content, ctype = fetcher(api_url, {"Accept": "application/vnd.github.raw+json", **auth})
            if "json" in ctype:
                doc = json.loads(content)
                if doc.get("encoding") != "base64" or not doc.get("content"):
                    raise ValueError("Unsupported GitHub README response")
                content = base64.b64decode(doc["content"]).decode("utf-8", errors="replace")
            item["body_excerpt"] = content[:MAX_TEXT]
            item["body_kind"] = "github_readme"
        else:
            content, ctype = fetcher(url)
            item["body_excerpt"] = readable_html(content) if "html" in ctype else content[:MAX_TEXT].strip()
            if not item["body_excerpt"]:
                raise ValueError("No readable body")
            item["body_kind"] = "article_excerpt"
        item["body_status"] = "ok"
    except Exception as exc:
        item["body_excerpt"] = ""
        item["body_kind"] = None
        item["body_status"] = "unavailable:" + type(exc).__name__
    return item
