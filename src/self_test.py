import os
import sys
import yaml
import subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def check_all(mode="test"):
    print("=" * 60)
    print("SELF-TEST: daily_news")
    print(f"Fecha: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Modo: {mode}")
    print("=" * 60)

    results = []
    ok = lambda name: results.append(("OK", name))
    fail = lambda name, msg: results.append(("FAIL", f"{name}: {msg}"))

    # 1. Python version
    print(f"\n[1/10] Python: {sys.version.split()[0]}")
    if sys.version_info >= (3, 10):
        ok("Python version")
    else:
        fail("Python version", "Necesita >= 3.10")

    # 2. Config file
    config_path = Path(__file__).parent.parent / "config.yml"
    if config_path.exists():
        try:
            with open(config_path) as f:
                cfg = yaml.safe_load(f)
            source_count = sum(len(v) for v in cfg.get("sources", {}).values())
            ok(f"Config: {source_count} fuentes RSS")
        except Exception as e:
            fail("Config YAML", str(e))
    else:
        fail("config.yml", "No encontrado")

    # 3. Dependencies
    deps = ["feedparser", "yaml", "requests", "sklearn", "numpy", "jinja2"]
    try:
        import groq; deps.append("groq")
    except ImportError:
        pass
    try:
        import google.genai; deps.append("google.genai")
    except ImportError:
        pass

    missing = []
    for d in deps:
        try:
            __import__(d)
        except ImportError:
            missing.append(d)
    if not missing:
        ok(f"Dependencias ({len(deps)}/ok)")
    else:
        fail(f"Dependencias faltantes", ", ".join(missing))

    # 4. API Keys (no mostrar valores!)
    if mode == "production":
        groq_key = os.environ.get("GROQ_API_KEY", "")
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        if groq_key:
            ok(f"GROQ_API_KEY configurada ({groq_key[:8]}...)")
        else:
            fail("GROQ_API_KEY", "No configurada")
        if gemini_key:
            ok(f"GEMINI_API_KEY configurada ({gemini_key[:8]}...)")
        else:
            fail("GEMINI_API_KEY", "No configurada")
    else:
        ok("API keys: no necesarias (modo test con Ollama)")

    # 5. Ollama (test mode)
    if mode == "test":
        try:
            resp = __import__("requests").get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json()["models"]]
                ok(f"Ollama: {len(models)} modelos ({', '.join(models[:3])}...)")
            else:
                fail("Ollama", f"HTTP {resp.status_code}")
        except Exception as e:
            fail("Ollama", f"No conecta: {e}")

    # 6. BD
    try:
        from src.db import init_db, get_articles_window
        init_db()
        articles = get_articles_window(7)
        ok(f"BD SQLite: {len(articles)} artículos en ventana")
    except Exception as e:
        fail("Base de datos", str(e))

    # 7. Scraper test (solo 1 feed)
    try:
        from src.rotation import RateLimiter, FeedCache
        rl = RateLimiter({"min_interval": 0})
        cache = FeedCache(ttl=0)
        resp = __import__("requests").get(
            "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
            headers={"User-Agent": "daily_news/1.0 test"},
            timeout=15
        )
        if resp.status_code == 200:
            import feedparser
            feed = feedparser.parse(resp.content)
            count = len(feed.entries)
            ok(f"Scraper El País: {count} entradas ({resp.elapsed.total_seconds():.1f}s)")
        else:
            fail("Scraper El País", f"HTTP {resp.status_code}")
    except Exception as e:
        fail("Scraper test", str(e))

    # 8. Espacio en disco
    try:
        import shutil
        total, used, free = shutil.disk_usage(Path(__file__).parent.parent)
        free_gb = free // (2**30)
        if free_gb >= 1:
            ok(f"Disco: {free_gb}GB libres")
        else:
            fail("Disco", f"Solo {free_gb}GB libres")
    except Exception as e:
        fail("Disco", str(e))

    # 9. Git (para deploy)
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            ok(f"Git: {result.stdout.strip()}")
        else:
            fail("Git", "No disponible")
    except Exception as e:
        fail("Git", str(e))

    # 10. SSH deploy target
    if mode == "production":
        try:
            host = cfg.get("deploy", {}).get("server_host", "viaje")
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", host, "echo OK"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                ok(f"SSH {host}: conecta")
            else:
                fail(f"SSH {host}", f"No conecta: {result.stderr[:100]}")
        except Exception as e:
            fail("SSH deploy", str(e))

    # RESULTADOS
    print("\n" + "=" * 60)
    print("RESULTADOS")
    print("=" * 60)
    passed = sum(1 for r in results if r[0] == "OK")
    failed = sum(1 for r in results if r[0] == "FAIL")
    for status, msg in results:
        icon = "✅" if status == "OK" else "❌"
        print(f"  {icon} {msg}")

    print(f"\n--- {passed} OK, {failed} FAIL ---")

    # Resumen
    if failed == 0:
        print("\n✅ AUTO-DIAGNÓSTICO: SISTEMA LISTO")
        return True
    else:
        print(f"\n⚠️  AUTO-DIAGNÓSTICO: {failed} problemas detectados")
        return False


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "test"
    check_all(mode)
