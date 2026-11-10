"""Durable Discord publication ledger: ambiguous sends require manual reconciliation.

Exactly-once delivery cannot be guaranteed across Discord and PostgreSQL.
A 'pending' claim is deliberately never auto-retried: the request may have
reached Discord even when our process lost the acknowledgement.
"""
from __future__ import annotations

import hashlib


def digest_key(messages):
    """Stable identity of a generated set of Discord messages."""
    raw = "\n<message-boundary>\n".join(messages)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class PublicationLedger:
    def __init__(self, database, key):
        self.database = database
        self.key = key

    def reserve_articles(self, articles):
        """Reserve every visible event before first webhook request.

        A second run with overlapping stories must be reviewed rather than
        generating another batch while publication history is uncertain.
        """
        from .published_history import event_key
        items = [item for article in articles
                 for item in [article, *(article.get("roundup_sources") or [])]]
        keys = sorted({event_key(item) for item in items})
        with self.database.connect() as conn:
            with conn.cursor() as cur:
                for key in keys:
                    cur.execute(
                        """INSERT INTO publication_events
                           (event_key, digest_key, status)
                           VALUES (%s, %s, 'reserved')
                           ON CONFLICT DO NOTHING
                           RETURNING event_key""",
                        (key, self.key),
                    )
                    if cur.fetchone() is None:
                        raise RuntimeError(
                            "PUBLICATION_EVENT_ALREADY_RESERVED: "
                            "check history/Discord before publishing again"
                        )

    def complete_articles(self):
        with self.database.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE publication_events SET status = 'sent'
                       WHERE digest_key = %s AND status = 'reserved'""",
                    (self.key,),
                )

    def claim(self, index, body):
        fingerprint = hashlib.sha256(body.encode("utf-8")).hexdigest()
        with self.database.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO publication_messages
                       (digest_key, message_index, body_sha256, status)
                       VALUES (%s, %s, %s, 'pending')
                       ON CONFLICT DO NOTHING
                       RETURNING message_index""",
                    (self.key, index, fingerprint),
                )
                if cur.fetchone() is None:
                    cur.execute(
                        """SELECT status, body_sha256 FROM publication_messages
                           WHERE digest_key = %s AND message_index = %s""",
                        (self.key, index),
                    )
                    row = cur.fetchone()
                    if row and row[1] != fingerprint:
                        raise RuntimeError("PUBLICATION_CONFLICT: message contents changed")
                    if row and row[0] == "sent":
                        return False
                    raise RuntimeError(
                        "PUBLICATION_UNCERTAIN: check Discord before manually resolving "
                        f"message {index}; automatic retry disabled"
                    )
        return True

    def sent(self, index, discord_id=None):
        with self.database.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE publication_messages
                       SET status = 'sent', discord_message_id = %s, sent_at = NOW()
                       WHERE digest_key = %s AND message_index = %s
                         AND status = 'pending'""",
                    (discord_id, self.key, index),
                )
                if cur.rowcount != 1:
                    raise RuntimeError("PUBLICATION_STATE_ERROR: pending message missing")

    def all_sent(self, count):
        with self.database.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT count(*) FROM publication_messages
                       WHERE digest_key = %s AND status = 'sent'""",
                    (self.key,),
                )
                return cur.fetchone()[0] == count
