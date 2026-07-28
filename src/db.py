import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "news.db"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            country TEXT NOT NULL,
            lang TEXT NOT NULL,
            published TEXT,
            fetched TEXT DEFAULT (datetime('now')),
            embedding BLOB,
            cluster_id INTEGER,
            is_synced INTEGER DEFAULT 0,
            sync_group TEXT
        );

        CREATE TABLE IF NOT EXISTS word_frequencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            lang TEXT NOT NULL,
            date TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            UNIQUE(word, lang, date)
        );

        CREATE TABLE IF NOT EXISTS clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT,
            topic TEXT,
            size INTEGER,
            start_date TEXT,
            end_date TEXT,
            keywords TEXT,
            summary TEXT
        );

        CREATE TABLE IF NOT EXISTS sync_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            article_ids TEXT NOT NULL,
            sources TEXT NOT NULL,
            first_seen TEXT,
            last_seen TEXT,
            count INTEGER DEFAULT 1,
            is_editorial INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS feed_health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_name TEXT NOT NULL,
            feed_url TEXT NOT NULL,
            consecutive_failures INTEGER DEFAULT 0,
            last_ok TEXT,
            last_error TEXT,
            total_errors INTEGER DEFAULT 0,
            UNIQUE(feed_name)
        );

        CREATE TABLE IF NOT EXISTS pipeline_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            duration_seconds REAL,
            total_articles INTEGER DEFAULT 0,
            total_clusters INTEGER DEFAULT 0,
            total_syncs INTEGER DEFAULT 0,
            feeds_ok INTEGER DEFAULT 0,
            feeds_fail INTEGER DEFAULT 0,
            errors TEXT,
            status TEXT DEFAULT 'running'
        );

        CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(published);
        CREATE INDEX IF NOT EXISTS idx_articles_cluster ON articles(cluster_id);
        CREATE INDEX IF NOT EXISTS idx_word_freq_date ON word_frequencies(date);
        CREATE INDEX IF NOT EXISTS idx_sync_topic ON sync_events(topic);
    """)
    conn.commit()
    try:
        conn.execute("ALTER TABLE sync_events ADD COLUMN countries TEXT DEFAULT '[]'")
    except Exception:
        pass
    conn.close()


def save_articles(articles):
    conn = get_conn()
    inserted = 0
    for a in articles:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO articles
                   (title, url, source, country, lang, published)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (a["title"], a["url"], a["source"], a["country"], a["lang"], a.get("published"))
            )
            if conn.total_changes > 0:
                inserted += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return inserted


def get_articles_window(days=7):
    conn = get_conn()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT * FROM articles WHERE fetched >= ? ORDER BY published DESC",
        (cutoff,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_articles_needing_embeddings(days=7):
    conn = get_conn()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT id, title FROM articles WHERE fetched >= ? AND embedding IS NULL ORDER BY published DESC",
        (cutoff,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_embedding(article_id, embedding):
    conn = get_conn()
    conn.execute(
        "UPDATE articles SET embedding = ? WHERE id = ?",
        (json.dumps(embedding), article_id)
    )
    conn.commit()
    conn.close()


def update_clusters(articles_with_clusters):
    conn = get_conn()
    for a in articles_with_clusters:
        conn.execute(
            "UPDATE articles SET cluster_id = ? WHERE id = ?",
            (a["cluster_id"], a["id"])
        )
    conn.commit()
    conn.close()


def get_words_in_window(days):
    conn = get_conn()
    cutoff = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
    rows = conn.execute(
        "SELECT word, lang, SUM(count) as total FROM word_frequencies "
        "WHERE date >= ? GROUP BY word, lang ORDER BY total DESC LIMIT 50",
        (cutoff,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_word_frequencies(frequencies):
    conn = get_conn()
    today = datetime.utcnow().date().isoformat()
    for word, lang, count in frequencies:
        conn.execute(
            """INSERT INTO word_frequencies (word, lang, date, count)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(word, lang, date) DO UPDATE SET count = count + ?""",
            (word, lang, today, count, count)
        )
    conn.commit()
    conn.close()


def get_sync_events(days=7):
    conn = get_conn()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT * FROM sync_events WHERE last_seen >= ? ORDER BY count DESC",
        (cutoff,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["sources"] = json.loads(d["sources"])
        except Exception:
            pass
        try:
            d["article_ids"] = json.loads(d["article_ids"])
        except Exception:
            pass
        try:
            d["countries"] = json.loads(d["countries"])
        except Exception:
            d["countries"] = []
        result.append(d)
    return result


def save_sync_event(topic, article_ids, sources, is_editorial=0, countries=None):
    conn = get_conn()
    existing = conn.execute(
        "SELECT id, count, article_ids FROM sync_events WHERE topic = ?", (topic,)
    ).fetchone()
    now = datetime.utcnow().isoformat()
    if existing:
        existing_ids = set(json.loads(existing["article_ids"]))
        existing_ids.update(article_ids)
        conn.execute(
            "UPDATE sync_events SET count = count + 1, last_seen = ?, article_ids = ? WHERE id = ?",
            (now, json.dumps(list(existing_ids)), existing["id"])
        )
    else:
        conn.execute(
            "INSERT INTO sync_events (topic, article_ids, sources, countries, first_seen, last_seen, count, is_editorial) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (topic, json.dumps(article_ids), json.dumps(sources), json.dumps(countries or []), now, now, len(article_ids), is_editorial)
        )
    conn.commit()
    conn.close()


def update_feed_health(feed_name, feed_url, ok, error=None):
    conn = get_conn()
    existing = conn.execute(
        "SELECT id, consecutive_failures, total_errors FROM feed_health WHERE feed_name = ?",
        (feed_name,)
    ).fetchone()
    now = datetime.utcnow().isoformat()
    if existing:
        if ok:
            conn.execute(
                "UPDATE feed_health SET consecutive_failures = 0, last_ok = ?, last_error = NULL WHERE id = ?",
                (now, existing["id"])
            )
        else:
            conn.execute(
                "UPDATE feed_health SET consecutive_failures = consecutive_failures + 1, last_error = ?, total_errors = total_errors + 1 WHERE id = ?",
                (error or "unknown", existing["id"])
            )
    else:
        if ok:
            conn.execute(
                "INSERT INTO feed_health (feed_name, feed_url, consecutive_failures, last_ok, total_errors) VALUES (?, ?, 0, ?, 0)",
                (feed_name, feed_url, now)
            )
        else:
            conn.execute(
                "INSERT INTO feed_health (feed_name, feed_url, consecutive_failures, last_error, total_errors) VALUES (?, ?, 1, ?, 1)",
                (feed_name, feed_url, error or "unknown")
            )
    conn.commit()
    conn.close()


def get_feeds_in_failure(min_consecutive=2):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM feed_health WHERE consecutive_failures >= ? ORDER BY consecutive_failures DESC",
        (min_consecutive,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def start_pipeline_log(run_id, started_at):
    conn = get_conn()
    conn.execute(
        "INSERT INTO pipeline_log (run_id, started_at, status) VALUES (?, ?, 'running')",
        (run_id, started_at)
    )
    conn.commit()
    conn.close()


def finish_pipeline_log(run_id, finished_at, duration, articles, clusters, syncs, feeds_ok, feeds_fail, errors=None):
    conn = get_conn()
    conn.execute(
        """UPDATE pipeline_log SET finished_at = ?, duration_seconds = ?,
           total_articles = ?, total_clusters = ?, total_syncs = ?,
           feeds_ok = ?, feeds_fail = ?, errors = ?, status = 'completed'
           WHERE run_id = ?""",
        (finished_at, duration, articles, clusters, syncs, feeds_ok, feeds_fail, errors, run_id)
    )
    conn.commit()
    conn.close()


def fail_pipeline_log(run_id, errors):
    conn = get_conn()
    conn.execute(
        "UPDATE pipeline_log SET status = 'failed', errors = ? WHERE run_id = ?",
        (errors, run_id)
    )
    conn.commit()
    conn.close()


def rotate_articles(days=7):
    conn = get_conn()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    cursor = conn.execute('DELETE FROM articles WHERE fetched < ?', (cutoff,))
    deleted_articles = cursor.rowcount
    cursor2 = conn.execute('DELETE FROM word_frequencies WHERE date < ?', (
        (datetime.utcnow() - timedelta(days=days)).date().isoformat(),))
    deleted_words = cursor2.rowcount
    cursor3 = conn.execute('DELETE FROM sync_events WHERE last_seen < ?', (cutoff,))
    deleted_syncs = cursor3.rowcount
    conn.commit()
    conn.close()
    return deleted_articles, deleted_words, deleted_syncs
