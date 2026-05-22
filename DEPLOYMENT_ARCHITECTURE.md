# Deployment & Real-Time Architecture Guide

> **Scope**: DigitalOcean Droplet deployment + real-time study rooms implementation plan.
> No code changes are included here — this is an architectural reference.

---

## Current State of Study Rooms

The study rooms feature is currently a UI shell with **no real-time backend**:

- All endpoints are REST-only — no WebSocket support exists
- WebRTC camera/mic/screen-share code captures local streams but they never leave the device — there is no signaling server, so peers cannot connect to each other
- Member lists are static database snapshots, not live updates
- Room chat does not exist

---

## 1. Real-Time Study Rooms Architecture

Making WebRTC work between real users requires three layers.

### Layer 1 — Signaling Server (WebSockets)

WebRTC peers must exchange SDP offers/answers and ICE candidates *through a server* before they can talk directly. This is the signaling layer.

**Recommended technology: `python-socketio` + FastAPI**

- Handles rooms, broadcasts, reconnection, and namespaces out of the box
- Has a well-documented JavaScript client (`socket.io-client`)
- Integrates cleanly with the existing FastAPI app — no full rewrite needed

Each study room maps to a Socket.IO room. Joining a room subscribes a client to all events in that room.

**Events to implement:**

| Event | Direction | Purpose |
|---|---|---|
| `join-room` | Client → Server | User enters a room |
| `leave-room` | Client → Server | User exits a room |
| `user-connected` | Server → Room | Broadcast new participant |
| `user-disconnected` | Server → Room | Broadcast departure |
| `offer` | Client → Server → Peer | SDP offer for WebRTC handshake |
| `answer` | Client → Server → Peer | SDP answer |
| `ice-candidate` | Client → Server → Peer | ICE candidate exchange |
| `chat-message` | Client → Server → Room | Text chat broadcast |

### Layer 2 — WebRTC Peer Connections (Frontend)

With signaling in place, each browser opens an `RTCPeerConnection` to every other participant. The existing `getUserMedia` and `getDisplayMedia` code already captures streams — it needs to be wired into actual peer connections with proper offer/answer/ICE negotiation.

**Topology recommendation:**

- **Mesh** (everyone connects to everyone): acceptable for rooms with up to ~6 participants. Simpler to implement.
- **SFU (Selective Forwarding Unit)**: required for larger rooms. More complex; consider open-source options like mediasoup or Janus if needed later.

Start with mesh — it covers the study room use case well.

### Layer 3 — STUN / TURN Servers (NAT Traversal)

Without this, users behind NAT or firewalls (nearly everyone) cannot establish direct peer-to-peer connections.

**STUN:**
Use Google's free public STUN servers for development and low-to-moderate traffic:
```
stun:stun.l.google.com:19302
stun:stun1.l.google.com:19302
```

**TURN:**
For production, run `coturn` (open-source) on the Droplet. It relays media when direct P2P fails — essential for reliability across different network environments.

> TURN traffic relays raw audio/video, which is bandwidth and CPU intensive. Account for this when sizing the Droplet.

### Text Chat

Text chat is simpler than video — it is just Socket.IO events with no WebRTC involved. Messages can optionally be persisted to a new `room_messages` database table for chat history.

---

## 2. Database: SQLite → PostgreSQL

**SQLite is not suitable for production.** It has no write concurrency — simultaneous requests from multiple users cause lock errors, and it cannot be shared across multiple processes.

### Recommended Migration Path

**Use DigitalOcean Managed PostgreSQL** (available as an add-on to any Droplet). Benefits:
- Automated backups
- Failover support
- Built-in connection pooling (PgBouncer)
- No manual maintenance

Alternatively, PostgreSQL can be installed on the same Droplet to reduce cost, but the managed service is preferable for anything publicly accessible.

### Code Changes Required

| Change | Detail |
|---|---|
| Install `psycopg2-binary` | PostgreSQL adapter for SQLAlchemy |
| Update `DATABASE_URL` | Change from `sqlite:///./Project.db` to `postgresql://user:pass@host/db` |
| Remove SQLite-specific config | Drop `connect_args={"check_same_thread": False}` |
| Add production engine options | `pool_size`, `max_overflow`, `pool_pre_ping=True` |
| Adopt Alembic for migrations | `Base.metadata.create_all` is not safe for production schema changes |
| One-time data migration | Export existing SQLite data and import into PostgreSQL |

---

## 3. DigitalOcean Droplet Architecture

### Recommended Stack

```
Internet
    │
    ▼
 Nginx  ─── HTTPS (Let's Encrypt / Certbot)
    │    ─── HTTP → HTTPS redirect
    │    ─── WebSocket proxy (Upgrade / Connection headers)
    │
    ▼
 Gunicorn + Uvicorn workers  (FastAPI application)
    │
    ├── REST API endpoints
    ├── Socket.IO signaling
    └── Static file serving (or offload to Nginx directly)
    │
    ▼
 PostgreSQL  (Managed DB add-on, or local install)

 coturn  (TURN server — separate port, e.g. 3478 / 5349)
```

### Component Responsibilities

**Nginx**
- Terminates SSL
- Proxies HTTP traffic to Gunicorn
- Proxies WebSocket traffic (requires `Upgrade` and `Connection` header forwarding)
- Can serve the `/frontend` static files directly, bypassing the Python process entirely

**Gunicorn + Uvicorn Workers**
- Standard production runner for FastAPI/ASGI applications
- Worker class: `uvicorn.workers.UvicornWorker`
- Socket.IO requires **sticky sessions** if running more than one worker — start with 1–2 workers

**Systemd**
- Manages the Gunicorn process
- Auto-restarts on crash
- Starts the service on Droplet reboot

**coturn**
- Open-source TURN/STUN server
- Runs as a separate process on the same Droplet
- Ports to open in the firewall: 3478 (STUN/TURN), 5349 (TLS), and a UDP range for media relay (e.g. 49152–65535)

### Recommended Droplet Size

| Use Case | Droplet Size |
|---|---|
| Development / Testing | 1 vCPU / 2 GB RAM |
| Production (with coturn) | **2 vCPU / 4 GB RAM minimum** |
| Production (heavy traffic) | 4 vCPU / 8 GB RAM |

TURN media relay is CPU and bandwidth intensive — do not undersize if expecting concurrent video sessions.

### Firewall Ports to Open

| Port | Protocol | Service |
|---|---|---|
| 22 | TCP | SSH |
| 80 | TCP | HTTP (redirects to HTTPS) |
| 443 | TCP | HTTPS + WSS |
| 3478 | TCP + UDP | STUN / TURN |
| 5349 | TCP + UDP | TURN over TLS |
| 49152–65535 | UDP | TURN media relay range |

---

## 4. Summary — What Needs to Be Built

| Component | Effort | Technology |
|---|---|---|
| WebSocket signaling server (backend) | Medium | `python-socketio` + FastAPI |
| WebRTC peer connection logic (frontend) | Medium | Browser WebRTC API |
| TURN server setup | Low (configuration) | `coturn` |
| Text chat in rooms | Low | Socket.IO events |
| SQLite → PostgreSQL migration | Low–Medium | `psycopg2`, Alembic |
| Nginx + SSL setup | Low | Nginx + Certbot |
| Process management | Low | Systemd + Gunicorn |

The **signaling server + WebRTC frontend wiring** is the largest piece of work. Everything else is infrastructure configuration. The `python-socketio` + browser WebRTC combination is well-documented, production-proven, and integrates naturally into the existing FastAPI structure without requiring a full rewrite.
