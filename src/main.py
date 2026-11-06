import argparse
import json
import os
from .core import TOPICS, hn_search, searx_search, dedup, ask_llm, build_report, save_outputs


def main():
    p = argparse.ArgumentParser(description='AI Research zero-cost-first smoke test')
    p.add_argument('--topic', choices=list(TOPICS), default='ai')
    p.add_argument('--live', action='store_true', help='Actually query public sources')
    p.add_argument('--ai', choices=['none', 'nvidia', 'zhipu'], default='none')
    p.add_argument('--output', default='output')
    args = p.parse_args()
    if args.live:
        items = []
        try:
            items.extend(hn_search(TOPICS[args.topic]))
        except Exception as e:
            print(f'Hacker News unavailable: {type(e).__name__}: {e}')
        searx = os.getenv('SEARXNG_URL')
        if searx:
            try:
                items.extend(searx_search(searx, TOPICS[args.topic]))
            except Exception as e:
                print(f'SearXNG unavailable: {type(e).__name__}: {e}')
    else:
        items = [
            {'title': 'Sample open-source AI research project',
             'url': 'https://example.org/research?utm_source=test',
             'source': 'fixture', 'published_at': '2026-11-06'},
            {'title': 'Duplicate sample', 'url': 'https://example.org/research',
             'source': 'fixture'}
        ]
    items = dedup(items)
    ai_text = None
    if args.ai != 'none':
        if not items:
            print('No collected articles. AI skipped.')
        else:
            prompt = ('請整理以下候選文章標題及網址，不能假裝讀過正文。'
                      '列出研究價值及下一步查證方向：\n'
                      + json.dumps(items[:10], ensure_ascii=False))
            ai_text = ask_llm(args.ai, prompt)
    report = build_report(items, ai_text)
    save_outputs(items, report, args.output)
    print(f'OK: {len(items)} unique links, AI={args.ai}, output={args.output}')
    if args.live and not items:
        raise SystemExit('No live sources available; no source results collected')


if __name__ == '__main__':
    main()
