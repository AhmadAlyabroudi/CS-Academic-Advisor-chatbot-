#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh  –  Pull latest code, install deps, migrate, and restart service.
# Called by GitHub Actions (CI/CD) or manually on the Droplet.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR="/var/www/justadvisor"
VENV="$APP_DIR/backend/venv/bin" # التأكد من مسار البيئة الوهمية الصحيح بالباك إند

cd "$APP_DIR"

echo "[deploy] Installing / updating Python dependencies..."
"$VENV/pip" install --upgrade pip
"$VENV/pip" install -r backend/requirements.txt
"$VENV/pip" install "bcrypt==4.0.1" # تثبيت إصدار بي كريبت المتوافق لمنع إيرور الـ passlib

echo "[deploy] Running database migrations (Alembic)..."
cd "$APP_DIR/backend"
"$VENV/alembic" upgrade head
cd "$APP_DIR"

# ── Auto-sync AI knowledge base to Pinecone ──────────────────────────────────
echo "[deploy] Auto-syncing AI Knowledge Base to Pinecone..."
"$VENV/python" backend/scripts/seed_knowledge_base.py || echo "⚠️ AI Seeding skipped or had non-critical issues."
# ────────────────────────────────────────────────────────

# ── Ensure .env exists (systemd EnvironmentFile= fails hard on missing file) ──
echo "[deploy] Checking .env file..."
if [ ! -f "$APP_DIR/backend/.env" ]; then
    cp "$APP_DIR/backend/.env.example" "$APP_DIR/backend/.env"
    echo "[deploy] WARNING: .env was missing — created from .env.example."
fi

# ── Ensure log directory exists with correct ownership ───────────────────────
sudo mkdir -p /var/log/justadvisor
sudo chown www-data:www-data /var/log/justadvisor

# ── Ensure systemd service is registered ─────────────────────────────────────
echo "[deploy] Ensuring systemd service is registered..."
SERVICE_FILE="$APP_DIR/deploy/systemd/justadvisor.service"
if ! systemctl cat justadvisor &>/dev/null; then
    echo "[deploy] Service not found — installing from $SERVICE_FILE"
    sudo cp "$SERVICE_FILE" /etc/systemd/system/justadvisor.service
    sudo systemctl daemon-reload
    sudo systemctl enable justadvisor
    echo "[deploy] Service installed and enabled."
else
    # Refresh the unit file in case it changed
    sudo cp "$SERVICE_FILE" /etc/systemd/system/justadvisor.service
    sudo systemctl daemon-reload
fi

# ── Start / restart ───────────────────────────────────────────────────────────
echo "[deploy] Starting / restarting application..."
if sudo systemctl restart justadvisor; then
    echo "[deploy] Done.  Service status:"
    sudo systemctl status justadvisor --no-pager -l
else
    echo "[deploy] ERROR: service failed to start — last 40 log lines:"
    sudo journalctl -xeu justadvisor.service --no-pager -n 40
    exit 1
fi