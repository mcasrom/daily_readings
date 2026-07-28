import re
import json
from datetime import datetime, timezone, timedelta

ACTOR_GROUPS = {
    "Russia": ["Russia", "Rusia", "Rusia", "Kremlin", "Putin", "Moscow", "Moscu"],
    "China": ["China", "Chine", "Beijing", "Xi Jinping", "Chinese", "China's"],
    "USA": ["USA", "EEUU", "Estados Unidos", "United States", "US", "Trump", "Biden", "Washington", "White House"],
    "EU": ["EU", "European Union", "Union Europea", "Europa", "Europe", "European", "Brussels", "Bruselas"],
    "Iran": ["Iran", "Tehran", "Teheran", "Iranian", "Jomeini", "Khamenei"],
    "Israel": ["Israel", "Israeli", "Tel Aviv", "Netanyahu", "Israel's"],
    "Ukraine": ["Ukraine", "Ucrania", "Kyiv", "Kiev", "Zelensky", "Zelenski", "Ukrainian"],
}

STANCE_CACHE = {}


def _matches_actor(title, keywords):
    title_lower = title.lower()
    for kw in keywords:
        if kw.lower() in title_lower:
            return True
    return False


def detect_actor_mentions(articles):
    mentions = {actor: [] for actor in ACTOR_GROUPS}
    for a in articles:
        title = a.get("title", "")
        for actor, keywords in ACTOR_GROUPS.items():
            if _matches_actor(title, keywords):
                mentions[actor].append(a)
    return {k: v for k, v in mentions.items() if v}


def classify_stance(title, actor, llm):
    cache_key = (title[:100], actor)
    if cache_key in STANCE_CACHE:
        return STANCE_CACHE[cache_key]
    prompt = "Classify the stance toward " + actor + " in this news headline.\nHeadline: " + title[:200] + "\nRespond ONLY with one word: pro, contra, or neutral."
    try:
        result = llm._query(prompt).strip().lower()
        if "pro" in result:
            stance = "pro"
        elif "contra" in result or "anti" in result or "negative" in result:
            stance = "contra"
        else:
            stance = "neutral"
    except Exception:
        stance = "neutral"
    STANCE_CACHE[cache_key] = stance
    return stance


def aggregate_stance(actor_mentions, llm):
    result = {}
    for actor, articles in actor_mentions.items():
        by_source = {}
        for a in articles:
            source = a.get("source", "unknown")
            stance = classify_stance(a.get("title", ""), actor, llm)
            if source not in by_source:
                by_source[source] = {"pro": 0, "contra": 0, "neutral": 0}
            by_source[source][stance] += 1
        result[actor] = by_source
    return result


def detect_coordination(sync_events, articles, window_hours=6):
    flagged = []
    for se in sync_events:
        if len(se.get("sources", [])) < 2:
            continue
        article_ids = se.get("article_ids", [])
        matching_articles = [a for a in articles if a.get("id") in article_ids]
        if len(matching_articles) < 2:
            continue
        try:
            from src.generator import _parse_date
            pub_dates = []
            for a in matching_articles:
                p = a.get("published", "")
                if p:
                    dt = _parse_date(p)
                    if dt:
                        pub_dates.append(dt)
            if len(pub_dates) >= 2:
                min_dt = min(pub_dates)
                max_dt = max(pub_dates)
                spread = (max_dt - min_dt).total_seconds() / 3600
                if spread <= window_hours:
                    flagged.append({
                        "topic": se.get("topic", ""),
                        "sources": se.get("sources", []),
                        "countries": se.get("countries", []),
                        "spread_hours": round(spread, 1),
                        "article_count": len(matching_articles),
                    })
        except Exception:
            continue
    return flagged
