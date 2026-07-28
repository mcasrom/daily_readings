import feedparser
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.rotation import RateLimiter, FeedCache
from src.db import update_feed_health


COUNTRIES = {
    "elpais.com": "espana", "elmundo.es": "espana",
    "lavanguardia.com": "espana", "eldiariocantabria.publico.es": "espana",
    "washingtonpost.com": "estados_unidos", "wsj.com": "estados_unidos",
    "cnn.com": "estados_unidos", "nytimes.com": "estados_unidos",
    "lemonde.fr": "francia", "lefigaro.fr": "francia",
    "bbc.co.uk": "reino_unido", "theguardian.com": "reino_unido",
    "corriere.it": "italia", "ilsole24ore.com": "italia",
    "spiegel.de": "alemania", "dw.com": "alemania",
    "folha.uol.com.br": "brasil", "oglobo.globo.com": "brasil",
    "g1.globo.com": "brasil",
    "lanacion.com.ar": "argentina", "elcohetealaluna.com": "argentina",
}


def detect_country(url):
    for domain, country in COUNTRIES.items():
        if domain in url:
            return country
    return "internacional"


def process_feed(source_name, source_url, lang, timeout=15):
    status = {"name": source_name, "url": source_url, "lang": lang, "ok": False, "articles": 0, "error": None}
    try:
        headers = {
            "User-Agent": "daily_news/1.0 (+https://github.com/mcasrom/daily_readings)"
        }
        resp = requests.get(source_url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except requests.Timeout:
        status["error"] = f"timeout (> {timeout}s)"
        print(f"  [TIMEOUT] {source_name} (> {timeout}s)")
        update_feed_health(source_name, source_url, False, status["error"])
        return [], status
    except Exception as e:
        error_msg = str(e)[:120]
        status["error"] = error_msg
        print(f"  [ERROR] {source_name}: {e}")
        update_feed_health(source_name, source_url, False, error_msg)
        return [], status

    articles = []
    for entry in feed.entries[:20]:
        article = {
            "title": entry.get("title", "").strip(),
            "url": entry.get("link", ""),
            "source": source_name,
            "country": detect_country(entry.get("link", "")),
            "lang": lang,
            "published": entry.get("published") or entry.get("updated") or datetime.utcnow().isoformat(),
        }
        if article["title"] and article["url"]:
            articles.append(article)

    status["ok"] = True
    status["articles"] = len(articles)
    print(f"  [OK] {source_name}: {len(articles)} artículos")
    update_feed_health(source_name, source_url, True)
    return articles, status


def _process_feed_wrapper(feed_cfg, country, rate_limiter, feed_cache):
    name = feed_cfg["name"]
    url = feed_cfg["url"]
    lang = feed_cfg["lang"]

    cached = feed_cache.get(url)
    if cached:
        print(f"  [CACHE] {name}: {len(cached)} artículos")
        return cached, {"name": name, "url": url, "lang": lang, "ok": True, "articles": len(cached), "error": None, "cached": True}

    rate_limiter.wait_if_needed(url)
    articles, status = process_feed(name, url, lang)

    if articles:
        feed_cache.set(url, articles)
    return articles, status


def scrape_all(sources, rate_limiter, feed_cache, max_feeds=None):
    all_articles = []
    all_status = []

    tasks = []
    processed = 0
    for country, feeds in sources.items():
        for feed_cfg in feeds:
            if max_feeds and processed >= max_feeds:
                break
            processed += 1
            tasks.append((country, feed_cfg))

    if max_feeds:
        tasks = tasks[:max_feeds]

    print(f"  [PARALLEL] Scrapeando {len(tasks)} feeds con ThreadPoolExecutor...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for country, feed_cfg in tasks:
            f = executor.submit(_process_feed_wrapper, feed_cfg, country, rate_limiter, feed_cache)
            futures[f] = (country, feed_cfg["name"])

        for f in as_completed(futures):
            country, name = futures[f]
            try:
                articles, status = f.result()
                all_status.append(status)
                if articles:
                    all_articles.extend(articles)
            except Exception as e:
                print(f"  [ERROR] {name}: {e}")
                all_status.append({"name": name, "url": "", "lang": "?", "ok": False, "articles": 0, "error": str(e)[:120]})

    print(f"\n[*] Total feeds procesados: {len(all_status)}")
    return all_articles, all_status
