#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh  –  Pull latest code, install deps, migrate, and restart service.
# Called by GitHub Actions (CI/CD) or manually on the Droplet.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR="/var/www/justadvisor"
VENV="$APP_DIR/venv/bin"

echo "[deploy] Pulling latest code..."
cd "$APP_DIR"
git fetch origin main
git reset --hard origin/main

echo "[deploy] Installing / updating Python dependencies..."
"$VENV/pip" install --upgrade pip
"$VENV/pip" install -r backend/requirements.txt

echo "[deploy] Running database migrations..."
cd "$APP_DIR/backend"
"$VENV/alembic" upgrade head

echo "[deploy] Ensuring systemd service is registered..."
SERVICE_FILE="$APP_DIR/deploy/systemd/justadvisor.service"
if ! systemctl cat justadvisor &>/dev/null; then
    echo "[deploy] Service not found — installing from $SERVICE_FILE"
    sudo cp "$SERVICE_FILE" /etc/systemd/system/justadvisor.service
    sudo systemctl daemon-reload
    sudo systemctl enable justadvisor
    echo "[deploy] Service installed and enabled."
fi

echo "[deploy] Starting / restarting application..."
sudo systemctl restart justadvisor

echo "[deploy] Done.  Service status:"
sudo systemctl status justadvisor --no-pager -l
