#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# initial_setup.sh  –  One-time server provisioning for a fresh Ubuntu 22.04
# Droplet.  Run as root (or with sudo) ONCE after creating the Droplet.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_URL="https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git"
APP_DIR="/var/www/justadvisor"
DOMAIN="yourdomain.com"

echo "════════════════════════════════════════"
echo "  JUST Advisor – Initial Server Setup  "
echo "════════════════════════════════════════"

# ── 1. System update & core packages ─────────────────────────────────────────
apt-get update -y && apt-get upgrade -y
apt-get install -y python3 python3-pip python3-venv \
    nginx git curl ufw certbot python3-certbot-nginx \
    postgresql-client coturn

# ── 2. Firewall ───────────────────────────────────────────────────────────────
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw allow 3478/tcp   # TURN
ufw allow 3478/udp   # TURN
ufw allow 5349/tcp   # TURN/TLS
ufw allow 5349/udp
ufw allow 49152:65535/udp  # TURN relay range
ufw --force enable
echo "Firewall configured."

# ── 3. Create app directory & clone repo ─────────────────────────────────────
mkdir -p "$APP_DIR"
cd "$APP_DIR"
if [ ! -d ".git" ]; then
    git clone "$REPO_URL" .
fi

# ── 4. Python virtual environment ────────────────────────────────────────────
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"
echo "Python dependencies installed."

# ── 5. .env file ──────────────────────────────────────────────────────────────
if [ ! -f "$APP_DIR/backend/.env" ]; then
    cp "$APP_DIR/backend/.env.example" "$APP_DIR/backend/.env"
    echo ""
    echo "⚠️  IMPORTANT: Edit $APP_DIR/backend/.env and fill in all CHANGE_ME values."
    echo "   Then re-run the deploy script to apply."
fi

# ── 6. Log directories ────────────────────────────────────────────────────────
mkdir -p /var/log/justadvisor /var/log/coturn
chown www-data:www-data /var/log/justadvisor

# ── 7. Nginx config ───────────────────────────────────────────────────────────
sed "s/yourdomain.com/$DOMAIN/g" "$APP_DIR/deploy/nginx.conf" \
    > /etc/nginx/sites-available/justadvisor
ln -sf /etc/nginx/sites-available/justadvisor /etc/nginx/sites-enabled/justadvisor
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
echo "Nginx configured."

# ── 8. SSL certificate via Certbot ───────────────────────────────────────────
echo ""
echo "Obtaining SSL certificate for $DOMAIN ..."
certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos \
    --email "admin@$DOMAIN" --redirect
echo "SSL certificate issued."

# ── 9. Systemd service ────────────────────────────────────────────────────────
cp "$APP_DIR/deploy/systemd/justadvisor.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable justadvisor
echo "Systemd service registered."

# ── 10. coturn ────────────────────────────────────────────────────────────────
cp "$APP_DIR/deploy/coturn/turnserver.conf" /etc/turnserver.conf
# Uncomment and set external-ip in /etc/turnserver.conf manually
systemctl enable coturn
echo "coturn configured (remember to set external-ip and credentials)."

# ── 11. Run database migrations ───────────────────────────────────────────────
echo ""
echo "Running Alembic migrations..."
cd "$APP_DIR/backend"
DATABASE_URL=$(grep DATABASE_URL .env | cut -d= -f2-)
DATABASE_URL=$DATABASE_URL "$APP_DIR/venv/bin/alembic" upgrade head
echo "Migrations applied."

# ── 12. Start application ─────────────────────────────────────────────────────
systemctl start justadvisor
echo ""
echo "✅  Setup complete.  Check status with: systemctl status justadvisor"
echo "   Then run the data migration if needed:"
echo "   cd $APP_DIR/backend && python migrate_sqlite_to_pg.py"
