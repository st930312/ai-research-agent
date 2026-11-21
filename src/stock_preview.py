"""Send one clearly marked stock briefing preview, without Neon reservations.

This script must never be used by the scheduled production digest. It requires
an explicit opt-in environment variable and does not touch published history.
"""
from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from . import editorial_digest as editorial
from .ai_scheduler import AIRequestScheduler
from .digest_services import StockService
from .wide_discord import send_wide_messages


def main():
    if os.getenv("SEND_STOCK_PREVIEW") != "true":
        raise RuntimeError("SEND_STOCK_PREVIEW=true required")
    if not os.getenv("NVIDIA_API_KEY") or not os.getenv("DISCORD_WEBHOOK_URL"):
        raise RuntimeError("Preview needs NVIDIA_API_KEY and DISCORD_WEBHOOK_URL")
    service = StockService()
    now = datetime.now(ZoneInfo("Asia/Taipei"))
    editorial.configure_ai_scheduler(AIRequestScheduler())
    try:
        candidates = service.collect()
        result = service.build(candidates, [], now)
    finally:
        editorial.configure_ai_scheduler(None)
    if len(result.messages) != 1:
        raise RuntimeError("Stock preview expected exactly one message")
    prefix = (
        "# 🧪 測試訊息｜台股速報候選版\n"
        "-# 此訊息供人工審核，不是正式發布；不寫入 Neon 歷史。\n\n"
    )
    body = prefix + result.messages[0]
    if len(body) > 2000:
        raise RuntimeError("Preview exceeds Discord 2,000-character limit")
    send_wide_messages([body])
    print("STOCK_PREVIEW_DISCORD_SENT=1; no Neon ledger writes", flush=True)


if __name__ == "__main__":
    main()
