"""Zero-cost-first research smoke test; Python standard library only."""
from __future__ import annotations
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = 'AIResearchMVP/0.1 (research prototype; respectful request rate)'
TOPICS = {
    'ai': 'AI LLM agent',
    'dev': 'open source developer tools',
    'tech': 'new technology product',
    'finance': 'semiconductor earnings',
}


def fetch_json(url: str, *, timeout: int = 12) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f'HTTP {response.status}')
        if 'json' not in response.headers.get('Content-Type', '').lower():
            raise ValueError('Non-JSON response')
        return json.load(response)


def hn_search(query: str, limit: int = 5, *, fetcher=fetch_json) -> list[dict]:
    qs = urllib.parse.urlencode({'query': query, 'tags': 'story', 'hitsPerPage': limit})
    payload = fetcher('https://hn.algolia.com/api/v1/search?' + qs)
    result = []
    for row in payload.get('hits', []):
        url = row.get('url') or ('https://news.ycombinator.com/item?id=' + str(row.get('objectID', '')))
        if url.startswith(('http://', 'https://')):
            result.append({'title': row.get('title') or '', 'url': url, 'source': 'hackernews',
                           'published_at': row.get('created_at'), 'score': row.get('points')})
    return result


def searx_search(base_url: str, query: str, limit: int = 5, *, fetcher=fetch_json) -> list[dict]:
    """Only use instances whose operators explicitly permit scripted requests."""
    base = base_url.rstrip('/')
    if not base.startswith('https://'):
        raise ValueError('SEARXNG_URL must be https://')
    url = base + '/search?' + urllib.parse.urlencode({'q': query, 'format': 'json'})
    payload = fetcher(url)
    result = []
    for row in payload.get('results', [])[:limit]:
        link = row.get('url') or ''
        if link.startswith(('https://', 'http://')):
            result.append({'title': row.get('title', ''), 'url': link, 'source': 'searxng',
                           'snippet': row.get('content', '')})
    return result


def canonical_url(link: str) -> str:
    p = urllib.parse.urlsplit(link)
    qs = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True)
          if not (k.lower().startswith('utm_') or k.lower() in {'fbclid', 'gclid'})]
    path = p.path.rstrip('/') or '/'
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), path,
                                   urllib.parse.urlencode(qs), ''))


def dedup(items: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for row in items:
        key = canonical_url(row['url'])
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def ask_llm(provider: str, prompt: str) -> str:
    """Strict opt-in. Never automatically fall back to a chargeable endpoint."""
    providers = {
       'nvidia': ('NVIDIA_API_KEY', 'https://integrate.api.nvidia.com/v1/chat/completions', 'z-ai/glm-5.3-flash'),
       'zhipu': ('ZHIPU_API_KEY', 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
                 os.getenv('ZHIPU_MODEL', 'glm-5.3-flash')),
    }
    if provider not in providers:
        raise ValueError('Provider must be nvidia or zhipu')
    if os.getenv('ENABLE_REAL_AI') != 'true':
        raise RuntimeError('Real AI disabled; set ENABLE_REAL_AI=true after confirming free entitlement')
    if provider == 'zhipu' and os.getenv('CONFIRM_ZHIPU_ZERO_COST') != 'true':
        raise RuntimeError('Zhipu account billing not verified; set CONFIRM_ZHIPU_ZERO_COST=true only after checking console')
    env, url, model = providers[provider]
    key = os.getenv(env)
    if not key:
        raise RuntimeError(f'Missing {env}')
    body = json.dumps({
        'model': model,
        'messages': [
            {'role': 'system', 'content': '你是研究整理助手。使用繁體中文。不得捏造來源；區分事實與推測。'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 700,
        'stream': False
    }).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={
        'Authorization': f'Bearer {key}', 'Content-Type': 'application/json', 'User-Agent': USER_AGENT},
        method='POST')
    with urllib.request.urlopen(req, timeout=100) as resp:
        data = json.load(resp)
    return data['choices'][0]['message'].get('content') or ''


def build_report(items: list[dict], ai_text: str | None = None) -> str:
    lines = ['# AI Research MVP — Smoke Test', '',
             f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
             '', f'Collected: {len(items)} unique links', '', '## Sources']
    for i, row in enumerate(items, 1):
        title = re.sub(r'[\r\n\[\]]', ' ', row['title'])
        lines.append(f"{i}. {title} — {row['url']} ({row['source']})")
    lines.extend(['', '## AI Analysis',
                  ai_text or 'Skipped: dry run / API not explicitly enabled.', ''])
    return '\n'.join(lines)


def save_outputs(items: list[dict], report: str, output: str = 'output') -> None:
    dest = Path(output)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / 'collected.json').write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
    (dest / 'report.md').write_text(report, encoding='utf-8')
