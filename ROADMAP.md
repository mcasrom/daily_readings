# Intelligence Hub — Roadmap

## Filosofía

> Laptop solo para test/desarrollo. Producción corre en heznert vía APIs externas (Groq + Gemini). Sin GPU necesaria.

## ✅ Completado

### FASE 0 — Fundación
- [x] Evaluar recursos: laptop (15GB/12c), heznert (4GB/2c/38GB), Pi (descartado)
- [x] Arquitectura híbrida: scraping + APIs cloud + static deploy
- [x] `config.yml` con 16 fuentes RSS de 7 países
- [x] `src/db.py` — SQLite schema (articles, clusters, sync_events, word_frequencies)
- [x] `src/rotation.py` — Rate limiting + cache con backoff exponencial
- [x] `src/scraper.py` — RSS collector con feedparser (15s timeout, max_feeds opcional)
- [x] `src/embeddings.py` — Gemini API (production) / TF-IDF (test)
- [x] `src/clusterer.py` — HDBSCAN clustering sobre embeddings + similitud coseno
- [x] `src/sync_detector.py` — Detectar misma noticia multi-fuente + editoriales
- [x] `src/analytics.py` — Word tracking 3/5/7 días + trending ratio
- [x] `src/generator.py` — Jinja2 → HTML estático + JSON
- [x] `src/deploy.py` — Git push a GitHub Pages + rsync a heznert
- [x] `main.py` — Orquestador completo (--fast para test rápido)
- [x] `src/self_test.py` — Auto-diagnóstico (10 tests)
- [x] Test end-to-end: 153 artículos, 27 clusters, 1 sincronizada, wordclouds

### FASE 1 — Core scraping & almacenamiento
- [x] Scraper funcional (16 feeds, 15s timeout, rate limiting)
- [x] SQLite con 153+ artículos en ventana
- [x] Cache de respuestas (TTL 30 min)

### FASE 2 — Clustering & sincronizadas
- [x] Embeddings TF-IDF (500d, char-wb ngrams 2-4)
- [x] HDBSCAN clustering (min_cluster_size=2)
- [x] Detección de noticias sincronizadas (cosine > 0.75)
- [x] Etiquetado de clusters vía LLM
- [x] Breaking news (≥3 artículos recientes, ≥2 fuentes)

### FASE 3 — Analítica de palabras
- [x] Extracción de keywords (stopwords multilingüe ES/EN/FR/IT/PT/DE)
- [x] Ventanas de 3/5/7 días
- [x] Trending topics (ratio entre ventanas)
- [x] Word clouds (15 imágenes: 5 idiomas × 3 ventanas)

### FASE 4 — HTML & deploy
- [x] Dashboard completo: titulares, clusters, sincronizadas, palabras, trending
- [x] Nubes de palabras, entidades NER, breaking news, timeline por cluster
- [x] Favoritos por fuente (localStorage, persiste entre visitas)
- [x] Contador de visitas (servicio ligero en heznert)
- [x] Archivo de 7 días con rotación automática
- [x] Tabs: Fuentes, Metodología (con caveat legal), About
- [x] OG preview + Twitter Cards + favicon
- [x] Tipografía Inter, responsive, dark theme
- [x] `deploy/nginx.conf` — Server block SSL-ready
- [x] `deploy/deploy-to-server.sh` — Deploy automático
- [x] `src/counter_server.py` — Microservicio contador
- [x] Repo GitHub: `github.com/mcasrom/intelligence-hub`

## 📋 Próximo (FASE 5+)

### Pendientes priorizados
- [ ] **Cron en heznert** — Pipeline automático cada 6h (scraping + clustering + gen)
- [ ] **DNS + SSL** — `news.viajeinteligencia.com` con Let's Encrypt
- [ ] **Groq + Gemini** — Claves en producción para embeddings y LLM reales
- [ ] **Cross-language sync** — Detectar misma noticia entre idiomas distintos
- [ ] **Sentiment analysis** — Tono por fuente/país
- [ ] **Evolución temporal** — Timeline gráfico de clusters día a día
- [ ] **Notificaciones Telegram** — Alertas de breaking news

### Ideas para futuro
- [ ] Mapa geopolítico con noticias plotadas
- [ ] PWA (instalable como app)
- [ ] Buscador sobre histórico SQLite
- [ ] Exportar PDF del briefing
- [ ] GitHub Actions CI/CD
- [ ] Panel de control histórico (último mes)
- [ ] API REST en heznert para `data.json`
- [ ] Integración GDELT (como en verificacion_news)

## Estructura actual

```
~/daily_news/
├── config.yml                 # Fuentes, APIs, thresholds, deploy
├── main.py                    # Orquestador
├── requirements.txt           # Dependencias
├── ROADMAP.md                 # Este archivo
├── .env.example               # Template de variables de entorno
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── db.py                  # SQLite schema + queries
│   ├── scraper.py             # RSS collector (16 feeds)
│   ├── rotation.py            # Rate limiting + cache
│   ├── embeddings.py          # Gemini API / TF-IDF
│   ├── clusterer.py           # HDBSCAN + cosine similarity
│   ├── sync_detector.py       # Cross-source sync + editoriales
│   ├── analytics.py           # Word tracking + trending
│   ├── llm.py                 # Groq / Ollama LLM
│   ├── advanced_analysis.py   # NER, breaking news, timeline, entidades
│   ├── wordcloud_gen.py       # WordCloud → PNG
│   ├── generator.py           # Jinja2 → HTML + JSON
│   ├── deploy.py              # Git push + rsync (Python)
│   ├── self_test.py           # Auto-diagnóstico
│   └── counter_server.py      # Microservicio contador visitas
├── templates/
│   ├── briefing.html          # Dashboard principal (460+ líneas)
│   └── clusters.html          # Página de clusters
├── deploy/
│   ├── nginx.conf             # Server block SSL-ready
│   └── deploy-to-server.sh    # Deploy automático a heznert
├── data/                      # SQLite (gitignored)
├── output/                    # HTML generado (gitignored)
│   ├── index.html
│   ├── clusters.html
│   ├── data.json
│   ├── images/ (wordclouds)
│   ├── favicon.png, preview.jpg
│   └── {YYMMDD}_day_briefing.html
```

## Notas técnicas

- **Embeddings**: Gemini `models/embedding-001` (768d). En test: TF-IDF 500d char-ngrams.
- **LLM**: Groq `llama3-70b-8192`. En test: Ollama tinyllama.
- **Clustering**: HDBSCAN con `min_cluster_size=2`.
- **Sync detection**: Cosine similarity ≥ 0.75 entre embeddings.
- **Rate limiting**: 15 min entre requests al mismo feed. Backoff 2^n + jitter.
- **Counter**: Microservicio Python en `127.0.0.1:9099`, proxy nginx `/api/count`.
- **Deploy**: `bash deploy/deploy-to-server.sh` → rsync + nginx + systemd.
