import os
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

COUNTER_FILE = Path("/var/www/daily_readings/.visit_counter")
DB_FILE = Path("/home/deploy/intelligence-hub/data/news.db")
VISITORS_DB = Path("/home/deploy/intelligence-hub/data/visitors.db")
CRON_LOG = Path("/home/deploy/intelligence-hub/cron.log")
UNIQUE_WINDOW_HOURS = 24


def _init_visitors_db():
    conn = sqlite3.connect(str(VISITORS_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS unique_visits (
            ip TEXT PRIMARY KEY,
            last_visit TEXT NOT NULL
        )
    """)
    conn.close()


def _is_unique_visitor(ip):
    conn = sqlite3.connect(str(VISITORS_DB))
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=UNIQUE_WINDOW_HOURS)).isoformat()
    row = conn.execute(
        "SELECT last_visit FROM unique_visits WHERE ip = ?", (ip,)
    ).fetchone()
    is_unique = False
    if row is None:
        is_unique = True
    else:
        last = datetime.fromisoformat(row[0])
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if (now - last) > timedelta(hours=UNIQUE_WINDOW_HOURS):
            is_unique = True
    if is_unique:
        conn.execute(
            "INSERT OR REPLACE INTO unique_visits (ip, last_visit) VALUES (?, ?)",
            (ip, now.isoformat()),
        )
        conn.commit()
        conn.execute(
            "DELETE FROM unique_visits WHERE last_visit < ?", (cutoff,)
        )
        conn.commit()
    conn.close()
    return is_unique


def _get_counter():
    if COUNTER_FILE.exists():
        try:
            return int(COUNTER_FILE.read_text().strip())
        except ValueError:
            pass
    return 0


def _set_counter(value):
    COUNTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    COUNTER_FILE.write_text(str(value))


class CounterHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if "/health" in self.path:
            self._handle_health()
        else:
            self._handle_counter()

    def _handle_health(self):
        health = {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
        try:
            conn = sqlite3.connect(str(DB_FILE))
            row = conn.execute("SELECT COUNT(*) FROM articles").fetchone()
            health["articles_total"] = row[0]
            row2 = conn.execute("SELECT MAX(fetched) FROM articles").fetchone()
            health["last_article"] = row2[0]
            row3 = conn.execute("SELECT COUNT(DISTINCT source) FROM articles").fetchone()
            health["sources"] = row3[0]
            conn.close()
        except Exception as e:
            health["status"] = "degraded"
            health["db_error"] = str(e)
        try:
            mtime = CRON_LOG.stat().st_mtime
            age_min = (datetime.now(timezone.utc).timestamp() - mtime) / 60
            health["cron_log_age_min"] = round(age_min, 1)
            if age_min > 400:
                health["status"] = "warning"
                health["cron_note"] = f"Cron log stale ({round(age_min)}min old)"
        except Exception:
            health["cron_log_age_min"] = -1
        code = 200 if health["status"] == "ok" else 503
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(health, indent=2).encode())

    def _handle_counter(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        count = _get_counter()
        if "visit=1" in self.path:
            client_ip = self.client_address[0]
            if _is_unique_visitor(client_ip):
                count += 1
                _set_counter(count)
        self.wfile.write(json.dumps({"count": count}).encode())

    def log_message(self, format, *args):
        pass


def main():
    _init_visitors_db()
    port = int(os.environ.get("PORT", 9099))
    server = HTTPServer(("127.0.0.1", port), CounterHandler)
    print(f"[Counter] http://127.0.0.1:{port} -> {COUNTER_FILE}")
    server.serve_forever()


if __name__ == "__main__":
    main()
