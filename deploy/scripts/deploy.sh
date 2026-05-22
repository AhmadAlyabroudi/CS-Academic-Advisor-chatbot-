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

echo "[deploy] Restarting application..."
sudo systemctl restart justadvisor

echo "[deploy] Done.  Service status:"
sudo systemctl status justadvisor --no-pager -l
