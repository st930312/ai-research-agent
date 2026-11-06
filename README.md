# Technology Intelligence Feed — free-endpoint-first

A **Traditional-Chinese categorized technology digest**, produced by GitHub Actions and NVIDIA NIM. It is a news briefing, **not** a research-report archive.

## Current editorial plan

- Target **15 stories**, flexible 10–20 only if credible and current candidates exist.
- Categories: **AI/LLM/Agent (5), GitHub open source (2), Software/DevOps (3), Technology/Industry (4), Fintech/Semiconductors (1)**.
- Each selected story receives **roughly 200–500 Traditional-Chinese characters** depending on substance. The model is instructed not to pad unsubstantiated claims.
- News gathering: **Hacker News (past 7 days), GitHub repository discovery, public AI/technology/software/fintech RSS (past 5 days)**.
- Editorial pipeline: metadata collection → one NVIDIA shortlist request → fetch excerpts/READMEs for selected stories → 3-story drafting batches → category-separated Discord embeds.
- An estimated **6 NVIDIA model calls** for 15 stories (maximum 7, no automatic retry, no paid fallback).
- No database, daily report storage, or cron schedule. Existing legacy smoke test workflows remain for debugging.

## Manual workflow (recommended)

Go to **Actions → Editorial Tech Briefing - Manual Preview → Run workflow**.

- `live_ai=false`, `send_discord=false`: source collection and unit tests only.
- `live_ai=true`, `send_discord=false`: AI creates a full preview in the Actions log, **without Discord delivery**.
- `live_ai=true`, `send_discord=true`: send category-separated Discord Embed messages.

The AI API credentials stay in GitHub Actions Secrets:
- `NVIDIA_API_KEY` — NVIDIA NIM free prototype endpoint
- `DISCORD_WEBHOOK_URL` — Discord HTTPS webhook URL

`GH_TOKEN` is supplied automatically from GitHub's workflow token; do not commit any credentials.

**Do not set `send_discord=true` before reviewing a preview.** Use the new editorial workflow rather than the legacy `Technology Digest - One-Time Preview` workflow, which produces the older short format.

## Quality notes

- GitHub discovery is *trending-like* discovery via GitHub repository search, **not** the official GitHub Trending ranking.
- When an article is unavailable, it can only be summarized based on limited metadata. The Discord output flags such entries.
- A date-window filter helps prevent older popular articles being mistaken for current developments.
- AI recommendations are checked for source IDs and category quotas; shortages are backfilled from dated metadata, not invented.
- Web/RSS/README content is treated as untrusted reference material, not instructions.
- RSS publishers retain links and attribution to the original articles. Generated summaries are commentary, not copies of publisher articles.
- Free-prototype model access is subject to NVIDIA's service limits and terms, and may change.

## Unit tests

```bash
python -m unittest discover -s tests -v
```

## Older prototype components

`src/research_smoke.py` and `src/main.py` are retained as earlier proof-of-concept utilities. The current digest entry point is `python -m src.editorial_digest` (source-only by default). GLM/Z.ai remains disabled pending provider-limit clarification.
