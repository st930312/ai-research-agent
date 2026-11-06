"""User-approved wide Discord Markdown layout, not embed cards."""
from __future__ import annotations
import json
import os
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

MAX_CONTENT = 1900
SPACER = "\u200b\n\n"
ENDING = "\n\n\u200b"

def safe(value):
    value = str(value or "").replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
    return re.sub(r"[`#]", "", value).strip()

def article_text(row, index):
    title = safe(row.get("title") or "未命名")[:150]
    body = str(row.get("ai_description") or "尚無摘要，請參考原文").strip()
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
    return f"## {index:02d}｜{title}\n\n{body}\n\n🔗 來源：{url}{extra}"

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

def format_wide_messages(articles, categories):
    total = len(articles)
    summary = (
        "# 🛰️ 今日科技快訊\n"
        f"-# 共 {total} 則｜繁體中文科技情報\n\n"
        "依分類閱讀：AI、開源、軟體工程、科技產業、電玩、金融科技。"
    )
    messages = [SPACER + summary + ENDING]
    for category, (heading, _quota, _color) in categories.items():
        group = [item for item in articles if item.get("category") == category]
        if not group:
            continue
        heading_text = f"# {heading}\n\n"
        current = heading_text
        for index, row in enumerate(group, 1):
            piece = article_text(row, index)
            joiner = "\n\n━━━━━━━━━━━━━━━━\n\n" if current != heading_text else ""
            if len(current) + len(joiner) + len(piece) + len(SPACER) + len(ENDING) <= MAX_CONTENT:
                current += joiner + piece
                continue
            if current != heading_text:
                messages.append(SPACER + current + ENDING)
            current = heading_text
            for segment in split_long_article(piece, MAX_CONTENT - len(heading_text) - len(SPACER) - len(ENDING)):
                if current != heading_text:
                    messages.append(SPACER + current + ENDING)
                    current = heading_text
                current += segment
        if current != heading_text:
            messages.append(SPACER + current + ENDING)
    if any(len(message) > 2000 for message in messages):
        raise ValueError("Discord message exceeds 2000 characters")
    return messages

def send_wide_messages(messages):
    url = os.getenv("DISCORD_WEBHOOK_URL") or ""
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in
        ("discord.com", "discordapp.com", "canary.discord.com", "ptb.discord.com")
        or "/api/webhooks/" not in parsed.path):
        raise RuntimeError("Missing or invalid official Discord webhook")
    for index, text in enumerate(messages, 1):
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
        print(f"DISCORD_MESSAGE_SENT={index}/{len(messages)}", flush=True)
        time.sleep(0.5)
