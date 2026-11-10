"""Conservative numeric-claim verification against collected evidence.

This is a deterministic guard, NOT a complete fact-checking system.
"""
from __future__ import annotations
import re

CLAIM = re.compile(r"(?<![\w])(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(?:%|％|億美元|億台幣|兆美元|億元|萬美元|倍)(?!\w)")


def numeric_claims(text):
    return {re.sub(r"\s+", "", match.group(0)).replace("％", "%")
            for match in CLAIM.finditer(text or "")}


def validate_source_grounding(summary, article):
    """Reject quantified assertions that have no matching source evidence."""
    sources = [article, *(article.get("roundup_sources") or [])]
    evidence = "\n".join(
        str(source.get("body_excerpt") or source.get("description") or "")
        + "\n" + str(source.get("title") or "")
        for source in sources
    )
    unsupported = numeric_claims(summary) - numeric_claims(evidence)
    if unsupported:
        raise ValueError("UNSUPPORTED_NUMERIC_CLAIM: " + ", ".join(sorted(unsupported)[:5]))
    return True
