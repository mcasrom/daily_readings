import sys; sys.path.insert(0, '.')
from src.db import get_conn
conn = get_conn()
rows = conn.execute("SELECT feed_name, consecutive_failures, total_errors, last_error FROM feed_health ORDER BY total_errors DESC").fetchall()
for r in rows:
    d = dict(r)
    err = d.get("last_error", "") or ""
    icon = "OK" if d["consecutive_failures"] == 0 and d["total_errors"] == 0 else "WARN" if d["consecutive_failures"] == 0 else "FAIL"
    print(f"{icon} {d['feed_name']:25s} fails={d['consecutive_failures']} total={d['total_errors']} {err[:80]}")
conn.close()
