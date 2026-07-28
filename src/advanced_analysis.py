import re
import json
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# ── ENTIDADES CONOCIDAS (fallback para modo test) ──
KNOWN_PERSONS = [
    "Trump", "Zelensky", "Putin", "Biden", "Lula", "Feijóo", "Sánchez",
    "Zapatero", "Orban", "Macron", "Meloni", "Milei", "Musk", "Netanyahu",
    "Carney", "Hegseth", "Xia", "Jinping", "Modi", "Erdogan", "Kim",
    "Guterres", "Starmer", "Le Pen", "Abascal",
]
KNOWN_ORGS = [
    "UE", "OTAN", "ONU", "FMI", "OMS", "OPEP", "EEUU", "HAMAS", "Hizbulá",
    "BRI", "TJUE", "FED", "BCE", "CIA", "FBI", "UME", "PP", "PSOE", "VOX",
    "M5S", "RNC", "G7", "G20", "BBC", "WSJ", "WP",
]
KNOWN_LOCATIONS = [
    "Ucrania", "Rusia", "Gaza", "Irán", "Israel", "China", "Arabia Saudí",
    "Siria", "Líbano", "Venezuela", "Brasil", "Cuba", "Corea", "Afganistán",
    "Marruecos", "Argelia", "Mali", "Níger", "Sudán", "Etiopía",
    "Guadalajara", "Madrid", "Barcelona", "Valencia", "Alicante", "Sevilla",
    "Bruselas", "Londres", "París", "Berlín", "Roma", "Washington",
    "Moscú", "Pekín", "Brasilia", "Buenos Aires", "México", "La Meca",
    "Almería", "Toledo", "Granada", "Málaga", "Bilbao", "Zaragoza",
]


def extract_entities(titles, mode="test", llm=None):
    if mode == "production" and llm:
        return _extract_entities_llm(titles, llm)
    return _extract_entities_pattern(titles)


def _extract_entities_pattern(titles):
    text = " ".join(titles)
    entities = {"persons": [], "organizations": [], "locations": [], "events": []}

    for p in KNOWN_PERSONS:
        if re.search(re.escape(p), text, re.IGNORECASE):
            entities["persons"].append(p)

    for o in KNOWN_ORGS:
        if re.search(rf"\b{re.escape(o)}\b", text, re.IGNORECASE):
            entities["organizations"].append(o)

    for l in KNOWN_LOCATIONS:
        if re.search(re.escape(l), text, re.IGNORECASE):
            entities["locations"].append(l)

    events_patterns = [
        (r"[Ii]ncendio", "Incendio forestal"),
        (r"[Tt]erremoto", "Terremoto"),
        (r"[Ii]mundación", "Inundación"),
        (r"[Aa]taque", "Ataque"),
        (r"[Gg]uerra", "Guerra"),
        (r"[Pp]andemia|[Ee]bola|[Cc]ovid", "Crisis sanitaria"),
        (r"[Ee]leccion", "Elecciones"),
        (r"[Pp]acto nuclear|[Aa]cuerdo nuclear", "Pacto nuclear"),
    ]
    seen_events = set()
    for pat, label in events_patterns:
        if re.search(pat, text) and label not in seen_events:
            entities["events"].append(label)
            seen_events.add(label)

    return entities


def _extract_entities_llm(titles, llm):
    text = "\n".join(titles[:10])
    prompt = f"""Extrae entidades de estas noticias. Responde SOLO con JSON:
{{"persons":[], "organizations":[], "locations":[], "events":[]}}

Noticias:
{text}"""
    try:
        result = llm._query(prompt)
        return json.loads(result)
    except Exception:
        return _extract_entities_pattern(titles)


# ── BREAKING NEWS ──
def detect_breaking(clusters, db_articles, threshold_hours=48):
    now = datetime.now(timezone.utc)
    breaking = []

    for cid, cdata in clusters.items():
        articles = cdata.get("articles", [])
        if len(articles) < 3:
            continue

        recent = 0
        for a in articles:
            pub = a.get("published")
            if not pub:
                continue
            try:
                pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                if (now - pub_dt).total_seconds() < threshold_hours * 3600:
                    recent += 1
            except Exception:
                pass

        coverage = len(set(a["source"] for a in articles))
        countries = set(a["country"] for a in articles)

        if recent >= 3 and coverage >= 2:
            breaking.append({
                "cluster_id": cid,
                "size": len(articles),
                "recent_articles": recent,
                "sources": coverage,
                "countries": list(countries),
                "label": cdata.get("summary", f"Cluster {cid}"),
            })

    return sorted(breaking, key=lambda x: -x["size"])


# ── EVOLUCIÓN TEMPORAL ──
def compute_timeline(clusters):
    timeline = {}
    for cid, cdata in clusters.items():
        articles = cdata.get("articles", [])
        days = defaultdict(list)
        for a in articles:
            pub = a.get("published", "")
            try:
                d = datetime.fromisoformat(pub.replace("Z", "+00:00")).strftime("%y%m%d")
            except Exception:
                d = "unknown"
            days[d].append(a["title"])
        timeline[cid] = dict(sorted(days.items()))
    return timeline


# ── ENTIDADES GLOBALES (top mencionados en todo el corpus) ──
def compute_global_entities(articles, mode="test", llm=None):
    titles = [a["title"] for a in articles]
    entities = _extract_entities_pattern(titles)

    for cat in entities:
        counter = defaultdict(int)
        for a in articles:
            for ent in entities[cat]:
                if ent.lower() in a["title"].lower():
                    counter[ent] += 1
        entities[cat] = dict(sorted(counter.items(), key=lambda x: -x[1])[:10])

    return entities
