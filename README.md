# Technology Intelligence Feed V4.3 (publication safety & observability)

15-story Traditional-Chinese technology, games, and Taiwan stock-market briefing. GitHub Actions + NVIDIA NIM + Discord wide-format Markdown.

## News selection

Target 15 current stories (as many as 10–20 only when strong sources exist):
- AI / LLM / Agent **4**
- GitHub Open Source **2**
- Software Engineering / DevOps **2**
- Technology Industry / New Technology **3**
- **Gaming discovery roundup: up to 1 slot** (1–3 noteworthy PC, console or mobile game and platform stories; omit if weak)
- **Global semiconductor and fintech industry outlook: 1 slot** (integrate up to 4 distinct international news events, focus on demand, supply chain, competition and policy, not individual stock picks)
- Taiwan Stock Market (all sectors) **1**

AI writes up to 200–500 Traditional-Chinese characters per story, adjusted to available evidence. The system discourages padding or unsupported claims.

## V4.2: Specific world-industry events, games, and active GitHub discoveries

The global semiconductor and fintech slot is a **fact-first international industry brief**: report each real event and evidence-backed industry significance separately; do not force unrelated sources into one purported trend. Draw from 2–4 independently audited, recent sources where available, explain global supply/demand, manufacturing, infrastructure, payments or regulatory implications. The separate Taiwan stock slot remains dedicated to Taiwan market context.

The gaming slot is **one curated roundup** with up to three concise, independent items: noteworthy platform/industry developments, distinctive new PC/console titles, and potentially interesting mobile games. Personal tastes are ranking bonuses rather than exclusion rules; routine preregistrations, unremarkable discounts and low-impact updates should not be selected. If nothing worthwhile exists, omit the slot rather than insert filler. Only AI-approved gaming candidates qualify; metadata-based backfill is disabled for gaming, and hard-coded gaming-title keyword gates are removed.

All displayed source URLs remain clickable, and each component of a roundup is separately stored in Neon after successful Discord delivery to prevent it from reappearing the next run. These roundups count as **one slot each**; the digest remains at most 15 editorial slots and does not pad weak days.

## Sources

- Hacker News Algolia: recent stories (7 days), searched by date
- TechCrunch AI / Fintech; Semiconductor Engineering; SemiWiki; Ars Technica AI / Science / Technology Lab; The Verge
- **Bahamut GNN**, **Gematsu**, **PC Gamer** RSS; shared AI considers Steam, launches, new titles, tests, important updates and mobile games, with no title-keyword exclusions
- **Yahoo Taiwan Stock** Taiwan-market RSS and **CNA** finance and securities RSS; select across all industries, financial stocks, shipping, traditional sectors, index moves, foreign institutional flows, regulatory announcements, and individual company earnings, not just technology/AI
- **The Register** DevOps RSS
- GitHub recently created or recently active established repository search (not official Trending), retaining the 90-day cooldown and genuine-release exception
- **GitHub Releases** for curated established projects (Go, React, Moby/Docker, Redis, Docker Compose, Kubernetes)

Headline/event near-duplicate suppression, Neon publication-history filtering and URL de-duplication occur before the AI selection. The editorial selection validates source IDs, categories, and fixed quotas, and supports clearly labeled metadata-based fallback when an AI shortlist is incomplete. RSS dates and HN dates are filtered to recent items. Source URL is always preserved.

## NVIDIA AI response diagnostics

Every NVIDIA call records the complete returned SSE stream and extracted content in GitHub Actions logs using `AI_DIAGNOSTIC` entries. HTTP failures include the response status and full error body; interrupted streams include the raw lines received before failure. The logger masks configured `NVIDIA_API_KEY`, `DATABASE_URL`, `DISCORD_WEBHOOK_URL`, `GH_TOKEN` and `GITHUB_TOKEN` values, and never prints request Authorization headers. Provider responses may contain public news excerpts and can be verbose; inspect and limit GitHub Actions log access and retention appropriately. A malformed JSON result continues to fail closed after bounded retries; diagnostics are not published to Discord.

## Workflow

**Daily delivery:** GitHub Actions `v3-tech-digest.yml` runs at **08:30 Asia/Taipei** (UTC cron `30 0 * * *`), with NVIDIA AI and Discord sending automatically enabled only for the scheduled event. GitHub Actions cron runs may be delayed by the platform. Manual dispatch keeps both `live_ai` and `send_discord` opt-in and defaults off. The completed one-time publishing workflow has been removed.


[Actions: Technology Briefing - Daily 08:30 Asia/Taipei](https://github.com/st930312/ai-research-agent/actions/workflows/v3-tech-digest.yml)

Manual inputs:
- `live_ai=false`, `send_discord=false`: offline unit tests and source collection.
- `live_ai=true`, `send_discord=false`: generate 15-story wide-format preview in GitHub Actions logs (no Discord).
- `live_ai=true`, `send_discord=true`: send the selected 15-story briefing to Discord.

Uses GitHub Actions Secrets `NVIDIA_API_KEY` and `DISCORD_WEBHOOK_URL` and automatic `github.token`. No application-level NVIDIA API call limit per execution; the provider's own rate limits and quotas still apply. No paid fallback. Incomplete AI bodies trigger at most three delayed, targeted retry calls (20/40/60 seconds plus jitter). Invalid AI JSON is retried up to three times with the same waits; unresolved content still blocks all Discord delivery. RSS, public article fetches and NVIDIA transport retry only transient failures (up to three retries: 429 at 60/90/120 seconds, other transient network/5xx at 15/30/60 seconds; plus jitter). `Retry-After` takes precedence when longer; permanent failures do not retry. Before the production test, manually verify the NVIDIA endpoint is free for your account.

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

The Neon history table holds event-identity summaries, full drafted article summaries, key entities, event type, original/related source links, and GitHub release tags (not complete daily reports). A publication ledger reserves article identities before the first Discord POST and
tracks each message as pending/sent. An ambiguous network failure is **not
automatically retried**; check Discord and reconcile the ledger manually before
another delivery. This intentionally favors avoiding duplicates over automatic
recovery. Database-backed `pipeline_runs` also stores source counts, AI
latencies, draft counts and delivery status. 
The pipeline checks 90 days of news, filters repeated links and near-identical headlines, and cools down repeated GitHub repository recommendations. It **actively checks new formal releases of previously recommended repos**; different versions can enter the candidate pool, but the AI audit must confirm a meaningful feature, compatibility, or security change. It writes publication records only after all Discord messages successfully send. Partial Discord delivery now stores per-message send state, but exactly-once
delivery is impossible to guarantee without a Discord-side idempotency key.
An ambiguous pending message must be manually reconciled. No automatic resend
is attempted. A live Discord send without `DATABASE_URL` fails closed to avoid losing publication history.

The [scheduled production workflow](https://github.com/st930312/ai-research-agent/actions/workflows/v3-tech-digest.yml) runs offline Python tests and checks the database if configured; manual `live_ai` and `send_discord` toggles control AI and delivery. Daily schedule: 08:30 Asia/Taipei (00:30 UTC); the scheduled event enables both AI and Discord.

**Verification status on 2026-11-09:** GitHub Actions confirmed Neon connectivity and schema migration. Fourteen articles actually sent to Discord on 2026-11-09 were recovered from that workflow's public output and added to the Neon history with original URLs and summarized content. V4 preview acceptance runs without sending Discord (`.github/workflows/v4-semantic-preview.yml`).

## Safety, cost, limitations

- **Scheduled daily delivery at 08:30 Taiwan time; no full report/artifact storage**. Publication metadata is stored in Neon PostgreSQL when configured.
- No SearXNG server currently needed.
- Sourced text is untrusted input, not commands. AI is prompted not to fabricate dates or metrics.
- GitHub release discovery checks a curated base list and up to 12 recently published repositories from Neon, using stable, recent releases. Star-count increases alone are not a significant update.
- Cross-source matching combines cheap URL/headline filters with a dedicated NVIDIA semantic-event audit. Different wording describing one real event should become one story. The audit is probabilistic (not a guarantee against every duplicate), and malformed or incomplete model output causes the run to stop rather than sending unchecked content.
- If source body is unavailable the post is flagged. Publisher content is used only as short reference excerpts, with links to original sources.
- Publisher RSS feeds and provider limits can change; checks and exceptions are logged.
- Only `v3-tech-digest.yml` (daily scheduled production + manual opt-in), `v4-semantic-preview.yml`
(non-publishing acceptance), and `python-ci.yml` (offline tests) are kept.
Runtime NVIDIA model selection uses `NVIDIA_MODEL` or the default in
`src/tech_digest.py`; the unused documentation-only models YAML was removed.
The news selection quotas and metadata backfill policy are unchanged.

## Local tests

```bash
python -m unittest discover -s tests -v
```

## Corrections and no-placeholder publishing

Every drafted article must have a substantial, non-placeholder body before any Discord send. An incomplete batch fails the workflow and writes no publication history rather than posting a headline-only digest. The one-time `v42-body-repair.yml` re-drafts only the three gaming and three semiconductor sources from the 2026-11-09 V4.2 delivery. It verifies both complete summaries before posting the correction and does not create duplicate history rows.
