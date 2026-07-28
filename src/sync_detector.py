import re
import json
from datetime import datetime
from src.clusterer import find_similar_articles


EDITORIAL_PATTERNS = {
    "es": ["editorial", "opinión", "columna", "análisis", "tribuna"],
    "en": ["editorial", "opinion", "column", "analysis", "view"],
    "fr": ["éditorial", "opinion", "chronique", "analyse", "tribune"],
    "it": ["editoriale", "opinione", "rubrica", "analisi"],
    "pt": ["editorial", "opinião", "coluna", "análise"],
    "de": ["Leitartikel", "Meinung", "Kolonne", "Analyse"],
}


def is_editorial(title, source, lang="es"):
    title_lower = title.lower()
    patterns = EDITORIAL_PATTERNS.get(lang, []) + ["editorial", "opinion"]
    for pat in patterns:
        if pat in title_lower:
            return True
    known_editorialists = ["Yves Thréard", "Milena Gabanelli", "editorial"]
    for k in known_editorialists:
        if k.lower() in title_lower:
            return True
    return False


def detect_sync_groups(articles, embeddings, threshold=0.75):
    groups = find_similar_articles(articles, embeddings, threshold)
    sync_events = []

    for group in groups:
        group_articles = [articles[i] for i in group]
        sources = list(set(a["source"] for a in group_articles))
        countries = list(set(a["country"] for a in group_articles))

        titles = [a["title"] for a in group_articles]
        topic = _extract_topic(titles)
        is_edit = any(
            is_editorial(a["title"], a["source"], a.get("lang", "es"))
            for a in group_articles
        )

        sync_events.append({
            "topic": topic,
            "article_ids": [a["id"] for a in group_articles if a.get("id")],
            "sources": sources,
            "countries": countries,
            "is_editorial": is_edit,
            "size": len(group),
            "articles": group_articles,
        })

    return sync_events


def _extract_topic(titles):
    if not titles:
        return "unknown"
    words = re.findall(r'\w+', titles[0])
    significant = [w for w in words if len(w) > 4]
    topic = " ".join(significant[:6]) if significant else titles[0][:60]
    return topic
