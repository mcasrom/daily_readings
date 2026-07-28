import re
from collections import Counter
from datetime import datetime, timedelta

STOPWORDS = {
    "es": ["el", "la", "los", "las", "un", "una", "y", "e", "o", "a", "en", "de",
           "del", "con", "por", "para", "que", "es", "se", "no", "su", "lo", "le",
           "al", "como", "mas", "pero", "sus", "este", "entre", "ya", "todo", "esta",
           "tras", "era", "sin", "sobre", "tambien", "tras", "fue", "ha", "han",
           "hay", "ser", "sido", "dos", "muy", "cada", "si", "asi", "solo",
           "espana", "espanol", "espanola", "espanoles", "espanolas",
           "españa", "español", "española", "españoles", "españolas",
           "dia", "dias", "día", "días", "ano", "anos", "año", "años", "personas", "persona", "gente",
           "tres", "mil", "millones", "nacional", "gobierno",
           "esta", "estan", "estaba", "hace", "hacen", "hacia",
           "nuevo", "nueva", "nuevos", "nuevas",
           "ultimo", "ultima", "ultimos", "ultimas", "parte", "vez", "veces",
           "pais", "paises", "madrid", "barcelona", "cantabria",
           "presidente", "ministro", "ministra", "general", "mundo",
           "video", "videos", "imagen", "imagenes", "foto", "fotos",
           "santander", "as", "ante", "bajo", "cabe", "durante", "mediante"],
    "en": ["the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
           "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
           "has", "have", "had", "do", "does", "did", "will", "would", "could",
           "should", "may", "might", "shall", "can", "its", "it", "as", "at",
           "that", "this", "these", "those", "not", "no", "so", "if", "all",
           "about", "after", "before", "between", "over", "under", "than",
           "united", "states", "america", "american", "britain", "british",
           "uk", "world", "new", "more", "out", "why", "how", "what", "who",
           "says", "said", "make", "made", "year", "years", "day", "days",
           "time", "people", "country", "part", "first", "last"],
    "fr": ["le", "la", "les", "un", "une", "des", "du", "de", "et", "est", "sont",
           "dans", "pour", "sur", "avec", "pas", "que", "qui", "dans", "plus",
           "tout", "ses", "son", "sa", "aux", "ces", "cette", "entre", "etait",
           "ont", "fait", "etre", "avoir", "tres", "aussi", "apres", "avant",
           "france", "francais", "francaise", "monde", "par", "contre", "pres",
           "ans", "jour", "jours", "personnes", "personne", "temps", "partie",
           "nouveau", "nouvelle", "nouveaux", "nouvelles", "video", "videos",
           "peut", "donne", "fait", "etat", "etats", "million", "apres"],
    "it": ["il", "lo", "la", "gli", "le", "un", "uno", "una", "del", "della",
           "dei", "delle", "di", "a", "in", "da", "con", "su", "per", "tra",
           "fra", "che", "e", "sono", "non", "si", "anche", "ha", "ho", "hanno",
           "era", "stato", "piu", "molto", "dopo", "prima", "sempre",
           "italia", "italiano", "italiana", "italiani", "italiane",
           "nel", "nella", "negli", "nelle", "sul", "sulla", "sugli", "sulle",
           "anno", "anni", "milioni", "giorno", "giorni", "tempo", "parte",
           "nuovo", "nuova", "nuovi", "nuove", "video", "persone",
           "sono", "stata", "stati", "stato", "stati", "essere"],
    "pt": ["o", "a", "os", "as", "um", "uma", "uns", "umas", "de", "do", "da",
           "dos", "das", "em", "no", "na", "nos", "nas", "para", "por", "com",
           "que", "e", "sao", "nao", "se", "mais", "mas", "foi", "era", "tem",
           "tem", "esta", "estao", "muito", "tudo", "cada", "entre", "apos",
           "brasil", "brasileiro", "brasileira", "brasileiros", "brasileiras",
           "ano", "anos", "año", "años", "mil", "milhoes", "dia", "dias", "día", "días", "pessoas", "pessoa",
           "sobre", "como", "julho", "sabado", "edicao", "jornal",
           "video", "videos", "veja", "diz", "aos",
           "novo", "nova", "novos", "novas", "tempo", "parte", "vez", "vezes",
           "governo", "pais", "paises", "contra", "entre", "cada",
           "primeiro", "primeira", "ultimo", "ultima", "depois", "entao"],
    "de": ["der", "die", "das", "den", "dem", "des", "ein", "eine", "einen",
           "einer", "eines", "und", "oder", "aber", "in", "auf", "mit", "von",
           "fur", "an", "aus", "bei", "nach", "um", "uber", "ist", "sind", "war",
           "wird", "nicht", "sich", "auch", "noch", "schon", "sehr", "durch",
           "deutschland", "deutsche", "deutscher", "deutsche", "deutschen",
           "jahr", "jahre", "jahren", "millionen", "tag", "tage", "tagen",
           "menschen", "zeit", "teil", "neue", "neuer", "neuen", "neues",
           "video", "videos", "bild", "bilder"],
}


def extract_keywords(title, lang="es"):
    words = re.findall(r'[a-zA-Záéíóúàèìòùâêîôûäëïöüñçãõ]+', title.lower())
    stop = STOPWORDS.get(lang, [])
    return [w for w in words if w not in stop and len(w) > 2]


def compute_frequencies(articles, windows=[3, 5, 7]):
    result = {}
    for days in windows:
        cutoff = datetime.utcnow() - timedelta(days=days)
        window_articles = [
            a for a in articles
            if a.get("published") and a["published"] >= cutoff.isoformat()
        ]

        lang_counters = {}
        for a in window_articles:
            lang = a.get("lang", "es")
            if lang not in lang_counters:
                lang_counters[lang] = Counter()
            keywords = extract_keywords(a["title"], lang)
            lang_counters[lang].update(keywords)

        result[days] = {}
        for lang, counter in lang_counters.items():
            result[days][lang] = counter.most_common(50)

    return result


def compute_trending(frequencies):
    trends = {}
    if 3 not in frequencies or 7 not in frequencies:
        return trends
    for lang in frequencies[3]:
        current = dict(frequencies[3].get(lang, []))
        previous = dict(frequencies[7].get(lang, []))
        word_scores = {}
        for word, count in current.items():
            prev_count = previous.get(word, 0)
            score = count / (prev_count + 1)
            word_scores[word] = {"current": count, "previous": prev_count, "ratio": round(score, 2)}
        sorted_words = sorted(word_scores.items(), key=lambda x: x[1]["ratio"], reverse=True)
        trends[lang] = dict(sorted_words[:20])
    return trends
