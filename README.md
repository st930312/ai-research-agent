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

## Neon PostgreSQL setup (V4)

This is a **Python news digest**, not a Node/Next.js app. A small `package.json` adds the requested `npm run build` validation (Python syntax + tests) and `npm start` (source collection + optional editorial). No JavaScript web server is deployed.

Neon target already selected: organization `org-fragrant-sound-80556159`, project `summer-sunset-79960113`, branch `production`.

On a computer with npm connectivity and Neon authentication, run:

```bash
npm i -g neon@latest
neon login
neon init -y --org-id org-fragrant-sound-80556159 --project-id summer-sunset-79960113 --branch production --services postgres
neon deploy
```

If global install fails, use `npx neon@latest` instead of `neon`. If sign-in opens a browser, finish authentication there. **Never commit `.env` or `.env.local`.**

Add the resulting **Postgres URL**, typically `DATABASE_URL`, to your GitHub repository's **Settings → Secrets and variables → Actions → New repository secret**, named `DATABASE_URL`. The Actions runner installs `psycopg[binary]` from `requirements.txt`; its V3 workflow will then test live connection, DDL, INSERT and transaction rollback with:

```bash
npm run build
npm run test:db
npm start
```

In normal operation, `src/published_history.py` creates its own minimal `published_events` table and index, loads 90 days of published metadata, filters old URLs and near-identical titles, applies a 90-day GitHub repository cooldown, and stores each selected item **only after all Discord messages are successfully delivered**. Important: if Discord delivers some messages and later fails, a retry can repeat the earlier messages; full per-message idempotent sending is a separate improvement. Until `DATABASE_URL` is set, live Discord sends fail safely rather than sending untracked repeat stories. Read-only source preview and tests still run.

```bash
python -m unittest discover -s tests -v
```

**Verification status on 2026-11-09:** GitHub Actions `npm run build` succeeded, 40 tests passed, `npm start` collected 85 news candidates, but the live Neon smoke test was **SKIPPED** because `DATABASE_URL` was not present in GitHub Actions Secrets. This environment could not install the Neon CLI due to npm registry DNS failure, and could not perform `neon init` or `neon deploy`. No Neon connection or database provisioning is claimed.

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
