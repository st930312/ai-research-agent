# Technology Intelligence Feed V3

15-story Traditional-Chinese technology and games briefing. GitHub Actions + NVIDIA NIM + Discord wide-format Markdown.

## News selection

Target 15 current stories (as many as 10–20 only when strong sources exist):
- AI / LLM / Agent **4**
- GitHub Open Source **2**
- Software Engineering / DevOps **2**
- Technology Industry / New Technology **4**
- Gaming / Steam **2**
- Fintech / Semiconductors **1**

AI writes up to 200–500 Traditional-Chinese characters per story, adjusted to available evidence. The system discourages padding or unsupported claims.

## Sources

- Hacker News Algolia: recent stories (7 days), searched by date
- TechCrunch AI / Fintech; Ars Technica AI / Science / Technology Lab; The Verge
- **Bahamut GNN** RSS, with Steam/PC and game-news relevance preference
- **The Register** DevOps RSS
- GitHub recently created project search (not official Trending)
- **GitHub Releases** for curated established projects (Go, React, Moby/Docker, Redis, Docker Compose, Kubernetes)

Headline/event near-duplicate suppression and URL de-duplication occur before the AI selection. The editorial selection validates source IDs, categories, and fixed quotas, and supports clearly labeled metadata-based fallback when an AI shortlist is incomplete. RSS dates and HN dates are filtered to recent items. Source URL is always preserved.

## Workflow

[Actions: V3 Technology Briefing - Manual](https://github.com/st930312/ai-research-agent/actions/workflows/v3-tech-digest.yml)

Manual inputs:
- `live_ai=false`, `send_discord=false`: offline unit tests and source collection.
- `live_ai=true`, `send_discord=false`: generate 15-story wide-format preview in GitHub Actions logs (no Discord).
- `live_ai=true`, `send_discord=true`: send the selected 15-story briefing to Discord.

Uses GitHub Actions Secrets `NVIDIA_API_KEY` and `DISCORD_WEBHOOK_URL` and automatic `github.token`. Maximum **7 NVIDIA AI calls** per execution; no paid fallback and no automatic AI retry. Before the production test, manually verify the NVIDIA endpoint is free for your account.

## Discord layout

No embeds: native, wide Discord messages, `#` category titles, `##` article headings, clear paragraphs, original source URLs, and invisible-guard spacing between messages. Text is broken at article/paragraph boundaries to respect Discord's 2,000-character message limit. No markdown-heavy cards.

## Safety, cost, limitations

- **No daily schedule, database, or report/artifact storage**.
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
