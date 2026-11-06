"""Optional Neon PostgreSQL storage. Not required for smoke test.
Install psycopg[binary] and set DATABASE_URL via Secrets, never commit credentials.
"""
import json
import os

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
 id BIGSERIAL PRIMARY KEY,
 url TEXT NOT NULL UNIQUE,
 title TEXT NOT NULL,
 source TEXT NOT NULL,
 published_at TEXT,
 collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE IF NOT EXISTS reports (
 id BIGSERIAL PRIMARY KEY,
 topic TEXT NOT NULL,
 content TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def persist(items, topic, report):
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise RuntimeError('DATABASE_URL missing')
    import psycopg
    with psycopg.connect(url, connect_timeout=12) as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
            for item in items:
                cur.execute(
                    """INSERT INTO articles (url,title,source,published_at,metadata)
                    VALUES (%s,%s,%s,%s,%s::jsonb) ON CONFLICT(url) DO NOTHING""",
                    (item['url'], item['title'], item['source'], item.get('published_at'),
                     json.dumps(item))
                )
            cur.execute('INSERT INTO reports (topic,content) VALUES (%s,%s)', (topic, report))
