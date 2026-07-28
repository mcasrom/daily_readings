import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent.parent / 'templates'
OUTPUT_DIR = Path(__file__).parent.parent / 'output'


def _ensure_dirs():
    TEMPLATES_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)


def _parse_date(date_str):
    s = date_str.strip()
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%d %b %Y %H:%M:%S %z',
        '%d %b %Y %H:%M:%S %Z',
        '%d %b %Y %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%d/%m/%Y',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(s)
    except Exception:
        return None

def _article_matches_date(article, date_str):
    published = article.get('published')
    if not published:
        return False
    dt = _parse_date(published)
    if dt is None:
        return False
    try:
        article_date = dt.strftime('%y%m%d')
        return article_date == date_str
    except Exception:
        return False


def generate_briefing(articles, clusters, sync_events, frequencies, trends, date_str=None, stance_data=None, coordination_flags=None, all_articles_in_window=None,
                      sources=None, llm_model=None, wordclouds=None,
                      breaking=None, entities=None, site_domain=None,
                      feed_status=None, is_index=True):
    _ensure_dirs()
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime('%y%m%d')

    archive = []
    for i in range(7):
        d = datetime.now(timezone.utc) - timedelta(days=i)
        ds = d.strftime('%y%m%d')
        f = OUTPUT_DIR / f'{ds}_day_briefing.html'
        archive.append({'date': ds, 'exists': f.exists(), 'label': d.strftime('%d/%m/%y')})

    # ── KPI Chart Data ──────────────────────────────────────────────
    chart_data = {'labels': [], 'articles': [], 'sources': [], 'clusters': [], 'editions': []}
    now_local = datetime.now(timezone.utc)
    for i in range(6, -1, -1):
        d = now_local - timedelta(days=i)
        ds = d.strftime('%y%m%d')
        label = d.strftime('%d/%m')
        chart_data['labels'].append(label)
        day_arts = [a for a in articles if _article_matches_date(a, ds)]
        chart_data['articles'].append(len(day_arts))
        active_srcs = len(set(a['source'] for a in day_arts))
        chart_data['sources'].append(active_srcs)
        day_clusters = sum(1 for c in clusters.values() if any(
            _article_matches_date(a, ds) for a in c.get('articles', [])
        ))
        chart_data['clusters'].append(day_clusters)
        edition_file = OUTPUT_DIR / f'{ds}_day_briefing.html'
        chart_data['editions'].append(ds if edition_file.exists() else None)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template('briefing.html')

    articles = [a for a in articles if _article_matches_date(a, date_str)]

    # Filter cluster articles to match the edition date
    filtered_clusters = {}
    for cid, cdata in clusters.items():
        fc = dict(cdata)
        fc['articles'] = [a for a in cdata.get('articles', []) if _article_matches_date(a, date_str)]
        fc['size'] = len(fc['articles'])
        if fc['size'] >= 2:
            filtered_clusters[cid] = fc
    clusters = filtered_clusters

    MAX_ARTICLES_PER_SOURCE = 8

    by_country = {}
    for a in articles:
        country = a.get('country', 'internacional')
        if country not in by_country:
            by_country[country] = {}
        source = a['source']
        if source not in by_country[country]:
            by_country[country][source] = []
        if len(by_country[country][source]) < MAX_ARTICLES_PER_SOURCE:
            by_country[country][source].append(a)

    real_counts = {}
    # Only count articles matching the current edition date
    for a in (all_articles_in_window or articles):
        if _article_matches_date(a, date_str):
            c = a.get('country', 'internacional')
            real_counts[c] = real_counts.get(c, 0) + 1

    all_sources = {}
    for country_key, feeds in (sources or {}).items():
        display_country = country_key.replace('_', ' ').title()
        all_sources[display_country] = {'sources': {}, 'total': real_counts.get(country_key, 0)}
        for feed in feeds:
            src_name = feed['name']
            lang = feed.get('lang', '')
            found_articles = by_country.get(country_key, {}).get(src_name, [])
            count = len(found_articles)
            all_sources[display_country]['sources'][src_name] = {
                'articles': found_articles,
                'lang': lang,
                'url': feed.get('url', ''),
                'count': count,
            }

    html = template.render(
        date=datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        date_str=date_str,
        by_country=by_country,
        all_sources=all_sources,
        clusters=clusters,
        sync_events=sync_events,
        frequencies=frequencies,
        trends=trends,
        sources=sources or {},
        llm_model=llm_model,
        wordclouds=wordclouds or {},
        breaking=breaking or [],
        entities=entities or {},
        feed_status=feed_status or [],
        stance_data=stance_data or {},
        coordination_flags=coordination_flags or [],
        site_domain=site_domain or 'viajeinteligencia.com',
        archive=archive,
        chart_data=chart_data,
        total_articles=len(articles),
        total_clusters=len(clusters),
        generated_at=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
    )

    output_path = OUTPUT_DIR / f'{date_str}_day_briefing.html'
    output_path.write_text(html, encoding='utf-8')
    print(f'  [OK] Briefing generado: {output_path}')
    if is_index:
        index_path = OUTPUT_DIR / 'index.html'
        index_path.write_text(html, encoding='utf-8')
        print(f'  [OK] Index actualizado: {index_path}')
    return output_path


def generate_clusters_page(clusters, date_str=None):
    _ensure_dirs()
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime('%y%m%d')
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template('clusters.html')
    html = template.render(
        date=datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        date_str=date_str,
        clusters=clusters,
        generated_at=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
    )
    output_path = OUTPUT_DIR / 'clusters.html'
    output_path.write_text(html, encoding='utf-8')
    print(f'  [OK] Clusters generados: {output_path}')


def generate_json_data(articles, clusters, sync_events, frequencies, trends, date_str=None):
    _ensure_dirs()
    data = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'total_articles': len(articles),
        'articles': articles[:100],
        'clusters': list(clusters.values()) if isinstance(clusters, dict) else clusters,
        'sync_events': sync_events[:20],
        'word_frequencies': frequencies,
        'trends': trends,
    }
    output_path = OUTPUT_DIR / 'data.json'
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'  [OK] JSON data: {output_path}')


def generate_health_json(run_id, start_time, total_articles, total_clusters, total_syncs,
                          feeds_ok, feeds_fail, errors=None, duration=None):
    _ensure_dirs()
    now = datetime.now(timezone.utc)
    critical_errors = [e for e in (errors or []) if "429" not in e and "LLM" not in e]
    health = {
        "status": "ok" if not critical_errors else "degraded",
        "run_id": run_id,
        "generated_at": now.isoformat(),
        "pipeline_date": start_time.strftime("%Y-%m-%d"),
        "pipeline_time": start_time.strftime("%H:%M:%S UTC"),
        "duration_seconds": round(duration, 1) if duration else None,
        "total_articles": total_articles,
        "total_clusters": total_clusters,
        "total_syncs": total_syncs,
        "feeds_ok": feeds_ok,
        "feeds_fail": feeds_fail,
        "feeds_total": feeds_ok + feeds_fail,
        "errors": errors or [],
        "version": "2.0",
    }
    output_path = OUTPUT_DIR / "health.json"
    output_path.write_text(json.dumps(health, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f'  [OK] Health JSON: {output_path}')
    return health
