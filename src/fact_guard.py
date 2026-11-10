"""Conservative deterministic checks for numeric claims in generated news.

This is not a substitute for human verification. We only block clearly
unsupported high-impact quantitative claims when article source text exists.
"""
from __future__ import annotations
import re

CLAIM = re.compile(r"(?<![\w])(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(?:%|％|億美元|億台幣|兆美元|億元|萬美元|倍)(?!\w)")


def numeric_claims(text):
    return {re.sub(r"\s+", "", m.group(0)).replace("％", "%")
            for m in CLAIM.finditer(text or "")}


def validate_source_grounding(summary, article):
    """Fail closed for suspicious numeric claims absent from fetched evidence.

    If full text is unavailable, return without claiming the article was
    verified. RSS metadata is a weaker reference and is accepted as evidence
    only when the article body is absent.
    """
    sources = [article, *(article.get("roundup_sources") or [])]
    evidence = "\n".join(
        str(source.get("body_excerpt") or source.get("description") or "")
        + "\n" + str(source.get("title") or "")
        for source in sources
    )
    claims = numeric_claims(summary)
    observed = numeric_claims(evidence)
    unsupported = claims - observed
    # Publish mode must not silently invent financial measurements or growth.
    if unsupported:
        raise ValueError("UNSUPPORTED_NUMERIC_CLAIM: " + ", ".join(sorted(unsupported)[:5]))
    return True
