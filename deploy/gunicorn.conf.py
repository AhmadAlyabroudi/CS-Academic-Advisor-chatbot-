workers      = 1
worker_class = "uvicorn.workers.UvicornWorker"
threads      = 4
timeout      = 120
keepalive    = 5

# ── Binding ───────────────────────────────────────────────────────────────────
bind = "127.0.0.1:8080"

# ── Logging ───────────────────────────────────────────────────────────────────
accesslog = "/var/log/justadvisor/access.log"
errorlog  = "/var/log/justadvisor/error.log"
loglevel  = "info"

# ── Process name ─────────────────────────────────────────────────────────────
proc_name = "justadvisor"

# ── Graceful restart ──────────────────────────────────────────────────────────
graceful_timeout = 30
preload_app      = True
