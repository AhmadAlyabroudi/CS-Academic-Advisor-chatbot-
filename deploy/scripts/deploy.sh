#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh  –  Pull latest code, rebuild Docker image, migrate, and restart.
# Called by GitHub Actions (CI/CD) or manually on the Droplet.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR="/var/www/justadvisor"
CONTAINER="justadvisor_chatbot"

cd "$APP_DIR"

# ── Stop any conflicting systemd services ─────────────────────────────────────
echo "[deploy] Ensuring no conflicting systemd services..."
for svc in justadvisor justadvisor-backend; do
    if systemctl is-active "$svc" &>/dev/null; then
        echo "[deploy] Stopping systemd service: $svc"
        sudo systemctl stop "$svc"
    fi
    if systemctl is-enabled "$svc" &>/dev/null; then
        sudo systemctl disable "$svc" 2>/dev/null || true
    fi
done

# ── Ensure .env exists ───────────────────────────────────────────────────────
echo "[deploy] Checking .env file..."
if [ ! -f "$APP_DIR/backend/.env" ]; then
    cp "$APP_DIR/backend/.env.example" "$APP_DIR/backend/.env"
    echo "[deploy] WARNING: .env was missing — created from .env.example."
fi

# ── Rebuild and restart Docker container ──────────────────────────────────────
echo "[deploy] Rebuilding Docker image..."
docker-compose build --no-cache

echo "[deploy] Restarting container..."
docker-compose down 2>/dev/null || true
docker-compose up -d

# Wait for the container to be ready
echo "[deploy] Waiting for container to start..."
sleep 5

# ── Run database migrations inside the container ─────────────────────────────
echo "[deploy] Running database migrations (Alembic)..."
docker exec "$CONTAINER" alembic upgrade head

# ── Auto-sync AI knowledge base to Pinecone ──────────────────────────────────
echo "[deploy] Auto-syncing AI Knowledge Base to Pinecone..."
docker exec "$CONTAINER" python scripts/seed_knowledge_base.py || echo "⚠️ AI Seeding skipped or had non-critical issues."

# ── Verify ────────────────────────────────────────────────────────────────────
echo "[deploy] Verifying deployment..."
if docker ps --filter "name=$CONTAINER" --filter "status=running" | grep -q "$CONTAINER"; then
    echo "[deploy] ✅ Container is running."
    docker ps --filter "name=$CONTAINER" --no-trunc --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
else
    echo "[deploy] ❌ Container failed to start. Logs:"
    docker logs --tail 40 "$CONTAINER"
    exit 1
fi