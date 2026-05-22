# Gunicorn configuration for production
# Run from the backend/ directory:
#   gunicorn -c ../deploy/gunicorn.conf.py main:socket_app

import multiprocessing

# ── Workers ───────────────────────────────────────────────────────────────────
# Socket.IO requires sticky sessions when using >1 worker.
# Start with 1 worker; add a Redis adapter (python-socketio[redis]) before
# scaling beyond 1.
workers      = 1
worker_class = "uvicorn.workers.UvicornWorker"
threads      = 4
timeout      = 120
keepalive    = 5

# ── Binding ───────────────────────────────────────────────────────────────────
bind = "127.0.0.1:8000"

# ── Logging ───────────────────────────────────────────────────────────────────
accesslog = "/var/log/justadvisor/access.log"
errorlog  = "/var/log/justadvisor/error.log"
loglevel  = "info"

# ── Process name ─────────────────────────────────────────────────────────────
proc_name = "justadvisor"

# ── Graceful restart ──────────────────────────────────────────────────────────
graceful_timeout = 30
preload_app      = True
