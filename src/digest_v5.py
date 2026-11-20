"""V5 single-process daily digest: three concurrent services, one NVIDIA lane.

Legacy src.editorial_digest.main remains available; this is the scheduled
entry point. Each service's Neon ledger and Discord publication are isolated.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from zoneinfo import ZoneInfo

from .ai_scheduler import AIRequestScheduler
from . import editorial_digest as editorial
from .digest_services import TechService, GamingService, StockService
from .publication import PublicationLedger, digest_key
from .published_history import PublishedHistory
from .wide_discord import send_wide_messages


class DigestOrchestrator:
    def __init__(self, services=None, scheduler=None, database=None):
        self.services = services or [
            TechService(), GamingService(), StockService()
        ]
        self.scheduler = scheduler or AIRequestScheduler()
        self.database = database

    def run(self, *, live_ai=False, send_discord=False, now=None):
        if send_discord and not live_ai:
            raise ValueError("Cannot send Discord with AI disabled")
        if send_discord and not (self.database or os.getenv("DATABASE_URL")):
            raise RuntimeError("DATABASE_URL required for durable Discord publication")
        now = now or datetime.now(ZoneInfo("Asia/Taipei"))
        database = self.database
        if database is None and os.getenv("DATABASE_URL"):
            database = PublishedHistory()
        history = []
        if database is not None:
            database.setup_and_probe()
            history = database.recent()
        run_id = os.getenv("GITHUB_RUN_ID") or str(uuid.uuid4())
        succeeded = []
        failed = {}
        editorial.configure_ai_scheduler(self.scheduler if live_ai else None)

        def build_one(service):
            candidates = service.collect()
            if not live_ai:
                count = len(candidates.get("news", [])) if isinstance(candidates, dict) else len(candidates)
                print(f"SERVICE_COLLECTION_ONLY name={service.name} candidates={count}",
                      flush=True)
                return None
            return service.build(candidates, history, now)

        try:
            with ThreadPoolExecutor(max_workers=len(self.services),
                                    thread_name_prefix="digest") as executor:
                futures = {
                    executor.submit(build_one, service): service.name
                    for service in self.services
                }
                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        result = future.result()
                        if result is None:
                            succeeded.append(name)
                            continue
                        for index, message in enumerate(result.messages, 1):
                            print(f"===== SERVICE_PREVIEW {name} "
                                  f"{index}/{len(result.messages)} =====", flush=True)
                            print(message, flush=True)
                        if send_discord:
                            ledger = PublicationLedger(
                                database, digest_key(result.messages))
                            if result.daily_identity:
                                ledger.reserve_daily_digest(name, result.daily_identity)
                            else:
                                ledger.reserve_articles(result.articles)
                            send_wide_messages(result.messages, ledger=ledger)
                            if not ledger.all_sent(len(result.messages)):
                                raise RuntimeError(f"PUBLICATION_INCOMPLETE service={name}")
                            if result.history_rows:
                                database.mark_sent([
                                    {**row, "title": row.get("published_title") or row.get("title")}
                                    for row in result.history_rows
                                ])
                            ledger.complete_articles()
                            print(f"SERVICE_DISCORD_SENT name={name} "
                                  f"messages={len(result.messages)}", flush=True)
                        if database is not None:
                            database.record_run(
                                f"{run_id}:{name}",
                                "published" if send_discord else "preview",
                                {**result.metrics,
                                 "articles": len(result.articles),
                                 "messages": len(result.messages)},
                            )
                        succeeded.append(name)
                    except Exception as exc:
                        failed[name] = type(exc).__name__
                        print(f"SERVICE_FAILED name={name} "
                              f"error={type(exc).__name__}: {exc}", flush=True)
                        if database is not None:
                            try:
                                database.record_run(
                                    f"{run_id}:{name}", "failed",
                                    {"error_type": type(exc).__name__})
                            except Exception as log_error:
                                print(f"SERVICE_LOG_ERROR name={name} "
                                      f"type={type(log_error).__name__}", flush=True)
        finally:
            editorial.configure_ai_scheduler(None)
        print("V5_RUN_SUMMARY=" + json.dumps(
            {"success": succeeded, "failed": failed, "live_ai": live_ai,
             "discord": send_discord}, ensure_ascii=False), flush=True)
        if not succeeded:
            raise RuntimeError("All digest services failed")
        # A partial failure does not undo independently completed publications.
        return {"success": succeeded, "failed": failed}


def main():
    DigestOrchestrator().run(
        live_ai=os.getenv("ENABLE_REAL_AI") == "true",
        send_discord=os.getenv("SEND_DISCORD") == "true",
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"V5_FATAL {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
