#!/usr/bin/env bash
# healthcheck.sh — Verifica que el pipeline se ejecute cada 6h
set -e

HEALTH_URL="https://news.viajeinteligencia.com/health.json"
CURL_TIMEOUT=10
MAX_AGE_SECONDS=21600  # 6h

HEALTH=$(curl -s --max-time $CURL_TIMEOUT "$HEALTH_URL" 2>/dev/null || echo "")

if [ -z "$HEALTH" ]; then
    echo "[ALERT] health.json no accesible"
    exit 1
fi

GENERATED=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('generated_at',''))" 2>/dev/null)

if [ -z "$GENERATED" ]; then
    echo "[ALERT] health.json malformado"
    exit 1
fi

NOW_TS=$(date -u +%s)
GEN_TS=$(date -u -d"$GENERATED" +%s 2>/dev/null || echo 0)
AGE=$((NOW_TS - GEN_TS))

STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null)

echo "health.json age=${AGE}s status=${STATUS}"

if [ $AGE -gt $MAX_AGE_SECONDS ]; then
    echo "[ALERT] Pipeline sin ejecutar en ${AGE}s"
    # Disparar alerta Telegram si hay token
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=⚠️ Pipeline caído: última ejecución hace ${AGE}s" \
            -d "parse_mode=HTML" > /dev/null
    fi
    exit 1
fi

if [ "$STATUS" != "ok" ]; then
    echo "[ALERT] Pipeline status: $STATUS"
fi

echo "[OK] Healthcheck pasado (${AGE}s / ${STATUS})"
