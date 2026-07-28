# Way Ahead · Intelligence Hub

## Status actual (27 Julio 2026)

### Pipeline
- [x] Scraping RSS: 18 fuentes, 7 países (ES, US, FR, UK, IT, DE, BR)
- [x] Embeddings: TF-IDF char-wb ngrams(2,4) 500d (fallback automático)
- [x] Clustering: HDBSCAN, ~250 clusters detectados por ventana
- [x] Sincronizadas: detección de noticias coordinadas entre medios (coseno ≥ 0.75)
- [x] Analítica: palabras clave ventanas 3d/5d/7d, trending por idioma (6 idiomas)
- [x] Enriquecimiento LLM: Groq (llama-3.3-70b-versatile) con truncado y JSON keys corregidas
- [x] Narrativa: stance detection pro/contra/neutral por actor geopolítico (Russia, China, USA, EU, Iran, Israel, Ukraine)
- [x] Coordinación editorial: detección de ventana temporal < 6h entre fuentes cubriendo mismo tema
- [x] Generación HTML+JSON: briefing diario, clusters, data.json, archivo 7 días
- [x] Deploy local: rsync a /var/www/daily_readings/ + chown
- [x] Cron: cada 6h (00:00, 06:00, 12:00, 18:00) con notificación Telegram
- [x] Counter service: PM2, visitantes únicos con SQLite, health endpoint
- [x] PWA: instalable en móviles y tablets con service worker

### Repositorio
- **URL:** https://github.com/mcasrom/intelligence-hub
- **Rama:** main
- **Stack:** Python 3.12 + scikit-learn + HDBSCAN + feedparser + Groq + Jinja2 + Chart.js
- **Tamaño:** ~800KB (código) + ~470MB (venv) + ~828KB (SQLite DB)

### Despliegue
- **Servidor:** Hetzner (178.105.80.193), usuario deploy
- **Ruta:** /home/deploy/intelligence-hub/
- **Web:** https://news.viajeinteligencia.com/ (estáticos en /var/www/daily_readings/)
- **Nginx:** SSL Let's Encrypt, redirect HTTP→HTTPS, denial de archivos sensibles
- **PM2:** intelligence-hub-counter (puerto 9099)
- **Base de datos:** SQLite WAL mode en data/news.db (~1420 artículos en ventana 7d)
- **GitHub backup:** push automático tras deploy (token personal)

### Consumo de recursos
- **Disco:** ~470MB (469MB venv + ~800KB código + ~828KB DB + ~1.8MB output)
- **RAM:** ~150-200MB durante ejecución del pipeline; 21MB counter service (permanente)
- **CPU:** ~30-60s por ciclo completo (depende de Groq y volumen de embeddings)
- **API:** Groq (llama-3.3-70b-versatile) ~10-15 requests por ciclo (5 clusters + N artículos para stance)
- **Red:** ~2-5MB por ciclo (RSS feeds) + ~88KB por deploy rsync
- **Caché:** FeedCache TTL 30min, STANCE_CACHE en memoria por ciclo

### Fuentes configuradas (18)
| País | Medios |
|------|--------|
| España | El País, El Mundo, La Vanguardia, El Diario Cantabria |
| EE.UU. | NYT, Washington Post, WSJ, Fox News |
| Francia | Le Monde, Le Figaro |
| Reino Unido | BBC News, The Guardian |
| Italia | Corriere della Sera, Il Sole 24 Ore |
| Alemania | Der Spiegel, Deutsche Welle |
| Brasil | Folha de S.Paulo, G1 Globo |

## Pendientes / Mejoras

### Corto plazo — Sprint actual: conseguir más Media News
- [ ] **Ampliar fuentes RSS:** añadir más medios por país (Reuters, AP, AFP, Al Jazeera, RT, Sputnik, etc.)
- [ ] **Ampliar actores geopolíticos:** India, Turquía, OTAN, Corea del Norte, Arabia Saudí
- [ ] **Mejorar stance detection:** prompt multilingüe + few-shot + confidence score
- [ ] **Healthcheck endpoint público:** /api/health con estado del pipeline
- [ ] **Logs rotativos:** actualmente cron.log crece sin límite
- [ ] **Dashboard de monitorización:** último ciclo, errores, stats, gráficas semanales

### Medio plazo
- [ ] **Noticias destacadas (breaking news):** detección de crecimiento súbito de keywords
- [ ] **Alertas Telegram por evento:** cuando un tema se sincroniza en ≥3 fuentes en < 1h
- [ ] **Backup automático de BD:** rsync diario a backup remoto o S3
- [ ] **Purgado de artículos > 30 días:** rotación actual solo limpia 7 días
- [ ] **API pública de datos:** endpoints REST para consultar artículos, clusters, syncs
- [ ] **Frontend dinámico:** filtros por actor, fuente, fecha; gráficos interactivos
- [ ] **Suscripciones por tema:** alertas personalizadas cuando un actor/país aparece con cierto sesgo

### Largo plazo
- [ ] **ML fine-tune para clasificación de narrativas:** modelo propio vs LLM externo
- [ ] **Fine-Grained stance:** detectar no solo pro/contra sino tipo de framing (victimización, amenaza, oportunidad, etc.)
- [ ] **Análisis de redes de fuentes:** qué medios se citan entre sí, detección de cámaras de eco
- [ ] **Interfaz multi-usuario:** selección de países/medios/temas por perfil

## Bugs conocidos (resueltos)
- ~~Groq devuelve 400 en algunos clusters (modelo o rate limit)~~ → Corregido: JSON keys con quotes en prompt + truncado de títulos
- ~~Sin GEMINI_API_KEY, embeddings usan TF-IDF (menor calidad)~~ → TF-IDF funciona aceptablemente con char-ngrams
- ~~deploy.py requiere sudo~~ → Configurado sudoers sin password para rsync
- ~~Solo 5 clusters pasados al generador (resto ignorados)~~ → Ahora todos los active_clusters se renderizan
- ~~FutureWarning HDBSCAN copy parameter~~ → Añadido copy=True

## Bugs conocidos (abiertos)
- Fox News feed puede devolver 0 artículos en fines de semana
- Groq 400 en ~5 clusters por ciclo (moderación de contenido, no crítico)
- CNN feed devuelve artículos de 2023 (reemplazado por Fox News)

## Changelog

### 2026-07-27
-  — stance detection (pro/contra/neutral) por actor geopolítico
- Coordinación editorial: detección de sincronización < 6h entre fuentes
- Secciones nuevas en web: Cobertura por bloque + Posible coordinación
-  — FASE 9: Análisis de Narrativa (7 actores, 630 arts clasificados)
- Fix: todos los active_clusters se pasan al generador (antes solo los 5 enriquecidos con LLM)
- Fix: copy=True en HDBSCAN (elimina FutureWarning de sklearn 1.10)
- Fix: JSON keys con quotes en prompt LLM (evita 400 de Groq por sintaxis inválida)
- Fix: deploy.py usa rsync en vez de cp -r
- Mejora: counter_server.py con health endpoint + visitantes únicos con SQLite
- Commit: 079eeda

### 2026-07-26
- Fix: añadir formato fecha con microsegundos para DW y feeds ISO
- Fix: Der Spiegel feed a edición alemana activa, DW usa updated como fallback
- Fix: reemplazar CNN (RSS roto, contenido 2023) por Fox News
- Fix: stopwords con tildes, sync_events sources/countries como listas
- Fix: artículos filtrados por fecha en cada edición + stopwords ampliadas
- Feat: KPI chart 7 días con Chart.js
- Feat: PWA instalable en móviles + service worker
- Feat: funnel guide modal interactivo
- Feat: diagnóstico de fuentes en dashboard
