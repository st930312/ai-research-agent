"""User-approved wide Discord Markdown layout, not embed cards."""
from __future__ import annotations
import json
import os
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from datetime import datetime
from zoneinfo import ZoneInfo

MAX_CONTENT = 1900
SPACER = "\u200b\n\n"
ENDING = "\n\n\u200b"

def safe(value):
    value = str(value or "").replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
    return re.sub(r"[`#]", "", value).strip()

def article_text(row, index):
    title = safe(row.get("title") or "未命名")[:150]
    body = str(row.get("ai_description") or "").strip()
    if not body or "本則 AI 摘要未完整產生" in body or "尚無摘要" in body:
        raise ValueError("Discord article has no real body; refusing to format")
    body = re.sub(r"@(everyone|here)", lambda m: "@\u200b" + m.group(1), body, flags=re.I)
    # Preserve meaningful paragraphs; do not reproduce malformed markdown headers.
    body = re.sub(r"(?m)^\s*#{1,6}\s+", "", body)
    url = row.get("url") or ""
    if not url.startswith(("https://", "http://")):
        raise ValueError("Invalid article link")
    details = []
    if row.get("source") in ("github_search", "github_release"):
        details.append("GitHub")
        if row.get("language"):
            details.append(safe(row["language"])[:25])
        if row.get("source") == "github_search" and isinstance(row.get("score"), int):
            details.append("⭐ " + str(row["score"]))
    if row.get("body_status") != "ok":
        details.append("⚠️ 來源正文未取得")
    extra = ("\n-# " + " · ".join(details)) if details else ""
    # Each independent roundup event must retain an auditable source link.
    sources = list(dict.fromkeys(
        source.get("url", "") for source in row.get("roundup_sources", [])
        if isinstance(source, dict) and source.get("url", "").startswith(("https://", "http://"))
    ))
    related = "".join(
        f"\n🔗 延伸來源 {num}：{link}"
        for num, link in enumerate(sources, 1) if link != url
    )
    return f"## {index:02d}｜{title}\n\n{body}\n\n🔗 來源：{url}{related}{extra}"

def split_long_article(piece, limit):
    """Fallback: split at a paragraph/line rather than truncate model output."""
    parts = []
    rest = piece
    while len(rest) > limit:
        cut = rest.rfind("\n\n", 200, limit)
        if cut < 0:
            cut = rest.rfind("\n", 200, limit)
        if cut < 0:
            cut = limit
        parts.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip()
    if rest:
        parts.append(rest)
    return parts

def format_wide_messages(articles, categories, issue_date=None):
    """Use one heading per category; keep same-category chunks visually contiguous.

    Discord limits content to 2,000 characters. Split at article boundaries
    whenever possible, with no repeated heading/outer spacer within a category.
    """
    total = len(articles)
    issue_date = issue_date or datetime.now(ZoneInfo("Asia/Taipei")).date()
    summary = (
        f"# 🛰️ {issue_date:%Y/%m/%d} 科技快訊\n"
        f"-# 共 {total} 則｜繁體中文科技情報\n\n"
        "依分類閱讀：AI、開源、軟體工程、科技產業、電玩、金融科技、台灣股市。"
    )
    messages = [SPACER + summary + ENDING]
    for category, (heading, _quota, _color) in categories.items():
        group = [item for item in articles if item.get("category") == category]
        if not group:
            continue
        heading_text = f"# {heading}\n\n"
        # The leading spacer appears only at a NEW category boundary.
        current = SPACER + heading_text
        for index, row in enumerate(group, 1):
            article = article_text(row, index)
            joiner = "\n\n━━━━━━━━━━━━━━━━\n\n" if index > 1 else ""
            remaining = joiner + article
            # A new Discord message is already a visual separator.
            if (current != SPACER + heading_text
                    and len(current) + len(remaining) + len(ENDING) > MAX_CONTENT):
                messages.append(current)
                current = ""
                remaining = article
            while remaining:
                # Keep the source URL with its article when it fits; don't chop
                # a normal 200-500 character article into separate messages.
                capacity = MAX_CONTENT - len(current) - len(ENDING)
                if len(remaining) <= capacity:
                    current += remaining
                    remaining = ""
                    break
                if current.strip("\u200b\n "):
                    # The current message already contains an article: finish
                    # it without trailing inter-category padding.
                    # For a long single article, the continuation below splits it.
                    if current != SPACER + heading_text:
                        messages.append(current)
                        current = ""
                        remaining = remaining.lstrip("\n")
                        continue
                capacity = MAX_CONTENT - len(current) - len(ENDING)
                cut = remaining.rfind("\n\n", 200, capacity)
                if cut == -1:
                    cut = remaining.rfind("\n", 200, capacity)
                if cut == -1:
                    cut = capacity
                current += remaining[:cut]
                messages.append(current)
                current = ""
                remaining = remaining[cut:].lstrip("\n")
        # Only the end of the entire category gets the closing blank lines.
        if current:
            messages.append(current + ENDING)
        elif messages:
            messages[-1] += ENDING
    if any(len(message) > 2000 for message in messages):
        raise ValueError("Discord message exceeds 2000 characters")
    return messages

def send_wide_messages(messages, ledger=None):
    url = os.getenv("DISCORD_WEBHOOK_URL") or ""
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in
        ("discord.com", "discordapp.com", "canary.discord.com", "ptb.discord.com")
        or "/api/webhooks/" not in parsed.path):
        raise RuntimeError("Missing or invalid official Discord webhook")
    for index, text in enumerate(messages, 1):
        if ledger is not None and not ledger.claim(index, text):
            print(f"DISCORD_ALREADY_SENT={index}/{len(messages)}", flush=True)
            continue
        data = json.dumps({
            "content": text,
            "allowed_mentions": {"parse": []},
            "flags": 4,
        }, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "AIResearchAgent/0.8"},
        )
        for attempt in (1, 2):
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    if response.status not in (200, 204):
                        raise RuntimeError(f"Discord HTTP {response.status}")
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt == 2:
                    raise
                delay = float(exc.headers.get("Retry-After", "1"))
                time.sleep(min(5, max(1, delay)))
        if ledger is not None:
            ledger.sent(index)
        print(f"DISCORD_MESSAGE_SENT={index}/{len(messages)}", flush=True)
        time.sleep(0.5)
