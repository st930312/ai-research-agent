# AI Research Agent — zero-cost-first MVP

A manual GitHub Actions smoke test for research source collection. No schedule, paid search services, real AI calls, or database writes are enabled by default.

## How to test

1. Open **Actions → AI Research - Manual Smoke Test → Run workflow**.
2. Run with `live=false` first (offline fixture + unit tests).
3. Run with `live=true` to query Hacker News Algolia API.
4. Download the `research-smoke-output` artifact and open `report.md` and `collected.json`.

Optional: set repository variable `SEARXNG_URL` only for a public instance explicitly permitting automated JSON queries.

## Local test

```bash
python -m unittest discover -s tests -v
python -m src.main
python -m src.main --live --topic ai
```

## Model probes (local only, opt-in)

The model interface supports NVIDIA and Zhipu using REST; **the GitHub workflow does not invoke AI**. Never commit API keys.

```bash
ENABLE_REAL_AI=true NVIDIA_API_KEY=your_key python -m src.main --live --ai nvidia
```

Zhipu additionally requires `CONFIRM_ZHIPU_ZERO_COST=true` after verifying your account's free entitlement. API access alone is not proof of free credits. NVIDIA trial access is also subject to provider limits and policies.

## Next phases

- Verify external search providers and their permission/JSON compatibility.
- Test an AI provider after confirming no-charge access.
- Provision Neon Free, then enable idempotent persistence from GitHub Actions.
- Add GitHub, arXiv, and RSS collectors.
- Enable scheduled runs only after reliability and zero-cost guardrails are validated.

Data scope: the smoke test handles headlines, metadata and links, not full article contents. It does not claim otherwise.
