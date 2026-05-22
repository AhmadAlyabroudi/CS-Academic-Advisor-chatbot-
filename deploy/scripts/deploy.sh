#!/bin/bash
set -e

echo "[deploy] Pulling latest code..."
cd /var/www/justadvisor
git fetch origin main
git reset --hard origin/main

echo "[deploy] Installing dependencies..."
./backend/venv/bin/pip install -r backend/requirements.txt
./backend/venv/bin/pip install "bcrypt==4.0.1"

echo "[deploy] Auto-syncing local SQLite data to PostgreSQL..."
./backend/venv/bin/python backend/migrate_sqlite_to_pg.py

echo "[deploy] Auto-syncing AI Knowledge Base..."
./backend/venv/bin/python backend/scripts/seed_knowledge_base.py

echo "[deploy] Restarting application..."
systemctl daemon-reload
systemctl restart justadvisor-backend
echo "[deploy] Production System is up-to-date and Live!"