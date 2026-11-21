"""Deterministic stock-brief safety checks independent of language models."""
from __future__ import annotations

import re

TECHNICAL_INDICATOR = re.compile(
    r"(?:年線|半年線|季線|月線|週線|MA\s*(?:5|10|20|60|120|240|250))",
    re.IGNORECASE,
)
NUMERIC_VALUE = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:點|元|%|％)?")
CLAUSE_SPLIT = re.compile(r"(?<=[。！？；;\n])")


def unsupported_indicator_issues(draft: dict, available: set[str] | None = None) -> list[dict]:
    """Block invented numeric technical indicators unless supplied as verified data.

    We deliberately do not infer MA levels from index price or from news titles.
    This only guards claims about numeric *technical indicators*; AI fact audit
    remains responsible for other facts and unverified media claims.
    """
    available = available or set()
    issues = []
    for section in ("market", "overnight", "events", "flows", "watch"):
        body = draft.get(section, "")
        if not isinstance(body, str):
            continue
        for sentence in CLAUSE_SPLIT.split(body):
            if not TECHNICAL_INDICATOR.search(sentence):
                continue
            if NUMERIC_VALUE.search(sentence) and sentence.strip() not in available:
                issues.append({
                    "section": section,
                    "claim": sentence.strip()[:260],
                    "reason": "未提供可驗證的均線歷史資料，禁止自行推算技術指標數值",
                })
    return issues


def safe_redact_sections(draft: dict, sections: set[str]) -> dict:
    """Remove entire unsupported paragraphs; never compose replacement market facts."""
    redacted = dict(draft)
    replacements = {
        "market": "台股確切行情與漲跌幅資料尚待可靠來源確認，避免引用未核實數值。",
        "overnight": "海外市場的具體漲跌幅與台指期夜盤數字尚待完整行情確認。",
        "events": "部分重大事件缺乏足夠的交叉佐證，本次先不列入未經證實的消息。",
        "flows": "法人買賣超與資金變動缺乏可核對數據，本次不推測資金流向。",
        "watch": "留意市場波動與後續官方公告；不將未經證實資訊當成交易建議。",
    }
    for key in sections:
        if key in replacements:
            redacted[key] = replacements[key]
    return redacted
