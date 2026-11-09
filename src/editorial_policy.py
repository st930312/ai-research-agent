"""Conservative editorial eligibility gates for the two curated roundup slots.

AI ranks/combines relevant evidence, but cannot relabel irrelevant content as
an industry trend. False negatives are preferable to fabricated synthesis.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

# Concrete companies, technologies, or market concepts; never infer a fintech
# / semiconductor trend from generic "technology", "AI", or "startups".
INDUSTRY_TERMS = re.compile(
    r"semiconductor|microelectronic|chipmaking|chipmaker|\bchips?\b|"
    r"foundry|wafer|lithograph|fabrication|\bHBM\b|\bDRAM\b|\bNAND\b|"
    r"advanced packaging|photonic|silicon photonics|"
    r"tsmc|samsung semiconductor|sk hynix|asml|micron|"
    r"fintech|banking|digital bank|neobank|payments?|payment network|"
    r"stablecoin|visa|mastercard|stripe|revolut|"
    r"金融科技|半導體|晶片|晶圓|記憶體|先進封裝|微電子|光刻|"
    r"數位銀行|行動支付|電子支付|支付系統|金融監管|金融基礎設施",
    re.I,
)

INDUSTRY_BLOCKED_SOURCES = {"github_search", "github_release"}
INDUSTRY_BLOCKED_HOSTS = {"github.com", "www.github.com", "youtube.com",
                          "www.youtube.com", "youtu.be"}

GAME_LOW_VALUE = re.compile(
    r"事前登錄|預先登錄|預約註冊|預約活動|"
    r"盒裝版|實體版|典藏版|合集|重新上架|折扣|降價|特價|促銷|"
    r"bundle|physical edition|pre.registration|discount|price cut|"
    r"周年紀念|週年紀念", re.I,
)
GAME_HIGH_VALUE = re.compile(
    r"Steam\\b|SteamOS|Steam Deck|Epic Games Launcher|"
    r"PlayStation|Xbox|Nintendo|任天堂|索尼|Valve|"
    r"跨平台|重大更新|重要更新|全新玩法|正式推出|全球上市|"
    r"正式上線|全球發售|新作|首度公開|首次公開|發表|"
    r"new game|launches|launching|new release|major update|"
    r"mobile game|手遊|手機遊戲|game industry|遊戲產業",
    re.I,
)

def industry_eligible(row):
    """Use title/short source metadata only, never AI-generated narrative."""
    host = (urlsplit(row.get("url", "")).hostname or "").lower()
    if row.get("source") in INDUSTRY_BLOCKED_SOURCES or host in INDUSTRY_BLOCKED_HOSTS:
        return False
    title = row.get("title") or ""
    return bool(INDUSTRY_TERMS.search(title))

def gaming_eligible(row):
    """Exclude routine low-value game announcements even if AI selects them."""
    title = row.get("title") or ""
    if GAME_LOW_VALUE.search(title):
        return False
    return bool(GAME_HIGH_VALUE.search(title))
