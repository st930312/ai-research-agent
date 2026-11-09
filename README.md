# Technology Intelligence Feed V3

15-story Traditional-Chinese technology, games, and Taiwan stock-market briefing. GitHub Actions + NVIDIA NIM + Discord wide-format Markdown.

## News selection

Target 15 current stories (as many as 10–20 only when strong sources exist):
- AI / LLM / Agent **4**
- GitHub Open Source **2**
- Software Engineering / DevOps **2**
- Technology Industry / New Technology **3**
- Gaming / Steam **2**
- Fintech / Semiconductors **1**
- Taiwan Stock Market (all sectors) **1**

AI writes up to 200–500 Traditional-Chinese characters per story, adjusted to available evidence. The system discourages padding or unsupported claims.

## Sources

- Hacker News Algolia: recent stories (7 days), searched by date
- TechCrunch AI / Fintech; Ars Technica AI / Science / Technology Lab; The Verge
- **Bahamut GNN** RSS, with Steam/PC and game-news relevance preference
- **Yahoo Taiwan Stock** Taiwan-market RSS and **CNA** finance and securities RSS; select across all industries, financial stocks, shipping, traditional sectors, index moves, foreign institutional flows, regulatory announcements, and individual company earnings, not just technology/AI
- **The Register** DevOps RSS
- GitHub recently created project search (not official Trending)
- **GitHub Releases** for curated established projects (Go, React, Moby/Docker, Redis, Docker Compose, Kubernetes)

Headline/event near-duplicate suppression, Neon publication-history filtering and URL de-duplication occur before the AI selection. The editorial selection validates source IDs, categories, and fixed quotas, and supports clearly labeled metadata-based fallback when an AI shortlist is incomplete. RSS dates and HN dates are filtered to recent items. Source URL is always preserved.

## Workflow

[Actions: V3 Technology Briefing - Manual](https://github.com/st930312/ai-research-agent/actions/workflows/v3-tech-digest.yml)

Manual inputs:
- `live_ai=false`, `send_discord=false`: offline unit tests and source collection.
- `live_ai=true`, `send_discord=false`: generate 15-story wide-format preview in GitHub Actions logs (no Discord).
- `live_ai=true`, `send_discord=true`: send the selected 15-story briefing to Discord.

Uses GitHub Actions Secrets `NVIDIA_API_KEY` and `DISCORD_WEBHOOK_URL` and automatic `github.token`. Maximum **7 NVIDIA AI calls** per execution; no paid fallback and no automatic AI retry. Before the production test, manually verify the NVIDIA endpoint is free for your account.

## Discord layout

No embeds: native, wide Discord messages, `#` category titles, `##` article headings, clear paragraphs, original source URLs, and invisible-guard spacing between messages. Text is broken at article/paragraph boundaries to respect Discord's 2,000-character message limit. No markdown-heavy cards.

## Neon PostgreSQL setup (V4; Python only)

This news collector is a **Python app running under GitHub Actions**. You do not need npm, Node.js, `neon init`, or `neon deploy` to use Neon PostgreSQL.

Existing Neon target: org `org-fragrant-sound-80556159`, project `summer-sunset-79960113`, branch `production`. In your [Neon Console](https://console.neon.tech/), select that project and branch, use **Connect** to copy the PostgreSQL connection string, and add it to the GitHub repository **Settings → Secrets and variables → Actions** as `DATABASE_URL`. **Do not commit, log, or share the connection string.** Both `.env` and `.env.local` are excluded from Git.

The workflow installs `psycopg[binary]` from `requirements.txt`. Python performs initialization of its own `published_events` table automatically when a DB connection is configured. To run locally after setting `DATABASE_URL` privately:

```bash
python -m pip install -r requirements.txt
python -m compileall -q src tests
python -m unittest discover -s tests -v
python -m src.published_history
python -m src.editorial_digest
```

The history database holds only published news metadata, **not complete reports**. The pipeline checks the past 90 days, filters repeated links and near-identical headlines, and cools down recently recommended GitHub repositories. It writes publication records only after all Discord messages successfully send. A partial Discord webhook failure can still deliver some messages without recording their state; per-message idempotency remains a future improvement. A live Discord send without `DATABASE_URL` fails closed to avoid losing publication history.

The [V3 Manual workflow](https://github.com/st930312/ai-research-agent/actions/workflows/v3-tech-digest.yml) runs offline Python tests and checks the database if configured; manual `live_ai` and `send_discord` toggles control AI and delivery. There is no daily schedule.

**Verification status on 2026-11-09:** Previous GitHub Actions tests passed and candidate collection worked, but live Neon connectivity was **not verified**, because `DATABASE_URL` was absent from GitHub Actions Secrets. No DB provision, deployment, or live table writes are claimed.

## Safety, cost, limitations

- **No daily schedule or report/artifact storage**. Publication metadata is stored in Neon PostgreSQL when configured.
- No SearXNG server currently needed.
- Sourced text is untrusted input, not commands. AI is prompted not to fabricate dates or metrics.
- GitHub release discovery uses only a small curated repository list, and stable, recent releases.
- Cross-source event matching is conservative title similarity. Different wording of the same story may still pass; future improvements could use AI semantic clustering.
- If source body is unavailable the post is flagged. Publisher content is used only as short reference excerpts, with links to original sources.
- Publisher RSS feeds and provider limits can change; checks and exceptions are logged.
- **Old workflows remain for development and testing**. Use the V3 workflow for current digests.

## Local tests

```bash
python -m unittest discover -s tests -v
```
