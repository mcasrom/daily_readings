#!/usr/bin/env bash
# deploy-to-server.sh
# Deploy Intelligence Hub a heznert
# Prereq: DNS news.viajeinteligencia.com → heznert IP + certbot SSL
# Uso: bash deploy-to-server.sh

set -e

SERVER="viaje"
REMOTE_PATH="/var/www/daily_readings"
COUNTER_SERVICE="daily-news-counter"
DOMAIN="news.viajeinteligencia.com"

echo "=========================================="
echo "Intelligence Hub — Deploy a $SERVER"
echo "=========================================="

# 1. Rsync archivos estáticos
echo ""
echo "[1/4] Subiendo estático a $SERVER:$REMOTE_PATH..."
rsync -avz --delete --exclude=.git output/ "$SERVER:$REMOTE_PATH/" 2>&1 | tail -3
echo "  OK"

# 2. Nginx config
echo ""
echo "[2/4] Configurando nginx para $DOMAIN..."
scp deploy/nginx.conf "$SERVER:/tmp/intelligence-hub-nginx.conf"
ssh "$SERVER" bash -c "'
sudo mv /tmp/intelligence-hub-nginx.conf /etc/nginx/sites-available/intelligence-hub
sudo ln -sf /etc/nginx/sites-available/intelligence-hub /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
'"
echo "  OK"

# 3. Contador service
echo ""
echo "[3/4] Instalando contador de visitas..."
scp src/counter_server.py "$SERVER:$REMOTE_PATH/counter_server.py"
ssh "$SERVER" bash -c "'
sudo tee /etc/systemd/system/$COUNTER_SERVICE.service > /dev/null <<EOF
[Unit]
Description=Intelligence Hub Visit Counter
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=$REMOTE_PATH
ExecStart=/usr/bin/python3 $REMOTE_PATH/counter_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable $COUNTER_SERVICE
sudo systemctl restart $COUNTER_SERVICE
'"
echo "  OK"

# 4. Certbot SSL (si no existe)
echo ""
echo "[4/4] Verificando SSL..."
CERT_EXISTS=$(ssh "$SERVER" "sudo certbot certificates 2>/dev/null | grep -c '$DOMAIN' || true")
if [ "$CERT_EXISTS" -eq 0 ]; then
    echo "  Solicitando certificado SSL para $DOMAIN..."
    ssh "$SERVER" "sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email news@viajeinteligencia.com || echo '  ⚠️  DNS debe apuntar primero. Ejecuta manual: sudo certbot --nginx -d $DOMAIN'"
else
    echo "  ✅ SSL ya configurado para $DOMAIN"
fi

# 5. Verificar
echo ""
echo "=== Verificación ==="
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN" 2>/dev/null || echo "DNS no resuelve")
echo "  https://$DOMAIN → HTTP $HTTP_CODE"

echo ""
echo "=========================================="
echo "Deploy completado"
echo "  https://$DOMAIN"
echo "  https://github.com/mcasrom/intelligence-hub"
echo "=========================================="
