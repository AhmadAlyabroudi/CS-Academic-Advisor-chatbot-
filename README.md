# JUST Advisor — CS Academic Portal

**Graduation Project 2 (GP2) · Jordan University of Science and Technology**  
**Developer:** Ahmad Alyabroudi · Computer Science Department · 2025 / 2026

---

## Overview

JUST Advisor is a full-stack web application that serves as an intelligent academic guide for Computer Science students at JUST. It combines a hybrid AI chatbot, real-time WebRTC study rooms, GPA tracking, and a course roadmap into one unified student portal.

| Subsystem | Stack |
|---|---|
| Student Portal & Roadmap | FastAPI · SQLAlchemy · PostgreSQL |
| Real-Time Study Rooms | WebRTC Mesh · Socket.IO · coturn |
| Hybrid AI Chatbot | Groq SDK · Llama 3.3 70B |

---

## Features

- **AI Academic Advisor** — Groq-powered academic advisor answers course and policy questions using official JUST data, with source-confidence badges (Official Source / AI-Generated Insight)
- **Interactive Course Roadmap** — Visual semester-by-semester roadmap allowing dynamic grade modifications, failed state highlights (red failing cards), and automatic prerequisite unlocking/locking updates
- **GPA Calculator** — Semester and cumulative GPA simulator with chart visualizations
- **Study Rooms** — Real-time WebRTC video/audio/chat rooms with Socket.IO lobby and TURN relay
- **Faculty Directory** — Office hours, email, and location for all CS department faculty
- **Course Catalog** — Full CS curriculum listing with prerequisites and clickable prereq links
- **Profile Management** — Edit personal info, change password, view academic standing, with dynamic country code phone validation and exactly 6-digit University ID verification

---

## Architecture

```
Internet
    │
    ▼
 Nginx  ──  HTTPS :443 (TLS via Certbot)
            WebSocket proxy  /socket.io/
            Static files     /frontend/
    │
    ▼
 Gunicorn + UvicornWorker  (1 worker — required for Socket.IO)
    │
    ├── FastAPI  REST API
    └── Socket.IO  Signaling Server
    │
    ▼
 PostgreSQL  (Managed DB or self-hosted)

 coturn  (TURN/STUN server — ports 3478, 5349, UDP 49152–65535)

AI Pipeline (per chatbot request):
  Question → Token Overlap Classifier (Stop-word filtering & ratio check)
           ↓ overlap ≥ 0.30              ↓ overlap < 0.30
     Llama Official Mode (In-context) Llama General Mode
     "Official Source" badge         "AI-Generated Insight" badge
```

---

## Project Structure

```
GP2 Project Website/
├── .github/
│   └── workflows/
│       ├── ci.yml              # Test on every push
│       └── deploy.yml          # Auto-deploy to Droplet on push to main
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── chatbot_controller.py   # GET /chat/history  POST /chat/ai
│   │   │   ├── config_controller.py    # GET /api/ice-servers
│   │   │   ├── course_controller.py
│   │   │   ├── faculty_controller.py
│   │   │   ├── gpa_controller.py
│   │   │   ├── roadmap_controller.py
│   │   │   ├── rooms_controller.py
│   │   │   ├── signaling_controller.py # Socket.IO events
│   │   │   └── student_controller.py
│   │   ├── core/
│   │   │   ├── ai_advisor.py           # HybridAdvisorChain
│   │   │   ├── constants.py
│   │   │   ├── database.py             # SQLAlchemy engine
│   │   │   └── socket_manager.py       # python-socketio AsyncServer
│   │   ├── models/                     # SQLAlchemy ORM models
│   │   └── schemas/                    # Pydantic schemas
│   ├── alembic/versions/               # Database migrations
│   ├── knowledge_base/
│   │   ├── just_cs_curriculum.txt      # CS course catalog with prerequisites
│   │   └── just_regulations.txt        # Graduation rules, GPA policies, FAQ
│   ├── scripts/
│   │   └── seed_knowledge_base.py      # Embeds .txt files → upserts to Pinecone
│   ├── .env.example
│   ├── main.py                         # App factory + router registration
│   └── requirements.txt
├── deploy/
│   ├── coturn/turnserver.conf
│   ├── gunicorn.conf.py
│   ├── nginx.conf
│   ├── scripts/
│   │   ├── deploy.sh                   # Rolling deploy script
│   │   └── initial_setup.sh            # One-time Droplet provisioning
│   └── systemd/justadvisor.service
└── frontend/
    ├── index.html          # Login page
    ├── signup.html / signup.js
    ├── chatbot.html        # AI chatbot with source badges
    ├── history.html        # Past consultation sessions
    ├── roadmap.html / roadmap.js
    ├── gpa.html / gpa.js
    ├── study-rooms.html
    ├── room.html           # WebRTC video/audio/chat room
    ├── faculty.html
    ├── courses.html
    ├── profile.html
    ├── sidebar.js          # Shared layout: sidebar + auth guard + meeting widget
    └── styles.css
```

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- Git

### Steps

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd "GP2 Project Website"

# 2. Create and activate a virtual environment
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — DATABASE_URL (PostgreSQL) and SECRET_KEY are required.

# 5. Run migrations
alembic upgrade head

# 6. Start the server
uvicorn main:socket_app --reload --port 8000

# 7. Open http://localhost:8000
```

> **Entry point is `main:socket_app`** — this wraps FastAPI inside the Socket.IO ASGI layer so both share port 8000.

### Enable AI Chatbot Locally

Without API keys the chatbot runs in demo mode. To enable full AI:

```bash
# Add to backend/.env
GROQ_API_KEY=your_groq_api_key

# Restart the server
uvicorn main:socket_app --reload --port 8000
```

---

## Environment Variables

All variables are loaded from `backend/.env`. Copy from `backend/.env.example`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Yes | — | Random 32-byte hex string |
| `DATABASE_URL` | Yes | — | Full PostgreSQL SQLAlchemy connection URL |
| `ENVIRONMENT` | No | `development` | `development` or `production` |
| `ALLOWED_ORIGINS` | No | `*` | Comma-separated CORS origins |
| `GROQ_API_KEY` | No* | — | Groq Llama 3 API service key |
| `TURN_SERVER_IP` | No | — | coturn Droplet public IP |
| `TURN_USERNAME` | No | — | coturn credential username |
| `TURN_CREDENTIAL` | No | — | coturn credential password |
| `LIVEKIT_API_KEY` | No | — | LiveKit token generation API key |
| `LIVEKIT_API_SECRET` | No | — | LiveKit token generation API secret |

\* Required for full AI functionality.

```bash
# PostgreSQL connection string format:
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME

# Generate a SECRET_KEY:
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## API Endpoints

Interactive docs available at `/docs` when the server is running.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/login` | Student login (form data) |
| `POST` | `/signup` | Student registration |
| `GET` | `/student/{id}` | Get student profile |
| `PUT` | `/student/{id}` | Update name / phone |
| `PUT` | `/student/{id}/password` | Change password |
| `GET` | `/roadmap/{id}` | Roadmap with grades |
| `POST` | `/roadmap/{id}/update-course` | Update course status/grade & cascade lock dependencies |
| `GET` | `/roadmap/{id}/sync-stats` | Recalculate credit counts |
| `GET` | `/roadmap/{id}/recalculate-gpa` | Recalculate and persist GPA |
| `GET` | `/faculty` | Faculty directory |
| `GET` | `/courses/` | Full course catalog |
| `GET` | `/gpa/{id}` | Student GPA data |
| `POST` | `/api/calculate-gpa` | Semester GPA calculator |
| `GET` | `/api/ice-servers` | STUN/TURN config for WebRTC |
| `GET` | `/rooms/` | List study rooms |
| `POST` | `/rooms/create` | Create a study room |
| `POST` | `/rooms/join` | Join a room |
| `POST` | `/rooms/leave` | Leave a room |
| `DELETE` | `/rooms/{type}/{id}` | Terminate a room (creator only) |
| `GET` | `/chat/history/{id}` | Load chat history |
| `POST` | `/chat/ai` | Hybrid RAG AI chatbot |

---

## Socket.IO Events

### Client → Server

| Event | Payload | Description |
|---|---|---|
| `join_room` | `{roomId, userId, name}` | Join a study room |
| `leave_room` | `{roomId, userId}` | Leave a study room |
| `offer` | `{target, sdp}` | WebRTC SDP offer |
| `answer` | `{target, sdp}` | WebRTC SDP answer |
| `ice_candidate` | `{target, candidate}` | Relay ICE candidate |
| `send_message` | `{roomId, userId, name, message}` | Room chat message |
| `join_lobby` | `{}` | Subscribe to room-list updates |
| `leave_lobby` | `{}` | Unsubscribe from lobby |
| `room_created` | `{}` | Notify lobby of new room |

### Server → Client

| Event | Payload | Description |
|---|---|---|
| `existing-users` | `[{sid, userId, name}]` | Current members (sent to joiner) |
| `user-joined` | `{sid, userId, name}` | New participant joined |
| `user-left` | `{sid, userId}` | Participant disconnected |
| `member-count` | `{count}` | Updated headcount |
| `offer` / `answer` | `{from, sdp}` | Relayed SDP |
| `ice-candidate` | `{from, candidate}` | Relayed ICE candidate |
| `receive-message` | `{userId, name, message, timestamp}` | Chat broadcast |
| `room-list-updated` | `{}` | Lobby refresh trigger |

---

## Hybrid AI Chatbot

The chatbot uses a two-path decision pipeline:

1. The student's question is embedded using `gemini-embedding-001` (768 dimensions)
2. Pinecone returns the top-3 most similar chunks from the JUST knowledge base
3. If any chunk scores ≥ 0.7, Gemini answers **only from that official data** → **Official Source** badge
4. If all scores < 0.7, Gemini answers as a general AI assistant → **AI-Generated Insight** badge

**Similarity threshold** is set in `backend/app/core/ai_advisor.py`:
```python
SIMILARITY_THRESHOLD = 0.7
```

**Adding more knowledge:** Drop any `.txt` file into `backend/knowledge_base/` and run `python scripts/seed_knowledge_base.py`. The seeder chunks, embeds, and upserts idempotently — no code changes needed.

---

## Database

The project uses **PostgreSQL** exclusively (local and production). Set `DATABASE_URL` in `backend/.env` before running anything.

```bash
# Apply schema migrations:
cd backend
alembic upgrade head
```

### Adding Students / Faculty via Seed

Use `db.merge()` in the `seed()` function in `backend/main.py`. This upserts records — if the primary key exists it updates, otherwise it inserts. No need to delete the database file.

---

## Production Deployment (DigitalOcean)

### Recommended Stack

- **Droplet**: Ubuntu 22.04 LTS, 2 vCPU / 4 GB RAM minimum (coturn is bandwidth-intensive)
- **Process manager**: Gunicorn + UvicornWorker, managed by systemd
- **Reverse proxy**: Nginx — terminates TLS, proxies WebSocket, serves static files
- **TURN server**: coturn on the same Droplet

### Firewall Ports

| Port | Protocol | Service |
|---|---|---|
| 22 | TCP | SSH |
| 80 | TCP | HTTP → HTTPS redirect |
| 443 | TCP | HTTPS + WSS |
| 3478 | TCP + UDP | STUN / TURN |
| 5349 | TCP + UDP | TURN over TLS |
| 49152–65535 | UDP | TURN media relay |

### Deployment Checklist

**Phase 1 — API Keys**
- [ ] Get a [Google AI Studio](https://aistudio.google.com/app/apikey) Gemini API key
- [ ] Get a [Pinecone](https://www.pinecone.io) API key
- [ ] Create Pinecone index: name `just-cs-advisor`, dimensions **768**, metric **cosine**, serverless

**Phase 2 — Infrastructure**
- [ ] Create DigitalOcean Droplet (Ubuntu 22.04, 2 GB+ RAM)
- [ ] Point domain DNS A records to the Droplet IP
- [ ] Edit `deploy/scripts/initial_setup.sh` — set `REPO_URL` and `DOMAIN`
- [ ] SSH as root and run `bash initial_setup.sh`

**Phase 3 — Configuration**
- [ ] Fill `backend/.env` on the Droplet (DATABASE_URL, SECRET_KEY, API keys, ALLOWED_ORIGINS)
- [ ] Set `external-ip=<Droplet IP>` in `/etc/turnserver.conf` and restart coturn
- [ ] Verify SSL: `certbot certificates`

**Phase 4 — Knowledge Base**
- [ ] Run `python scripts/seed_knowledge_base.py` (expect ~150 vectors indexed)
- [ ] Seed `student_verification` table with valid email/university_id pairs

**Phase 5 — CI/CD**
- [ ] Add GitHub Secrets: `DROPLET_HOST`, `DROPLET_USER`, `SSH_PRIVATE_KEY`
- [ ] Push to `main` and confirm both `CI` and `Deploy` Actions pass

**Phase 6 — Smoke Test**
- [ ] Sign up, log in, verify roadmap loads with grades
- [ ] Ask chatbot a course question → confirm **Official Source** badge
- [ ] Ask a general question → confirm **AI-Generated Insight** badge
- [ ] Create a study room from two different browsers; verify video, audio, and chat
- [ ] Test from two different networks to confirm TURN relay works

---

## CI/CD Pipeline

### `ci.yml` — Every push and PR to main

| Check | Detail |
|---|---|
| PostgreSQL service container | Real DB for migration tests |
| `alembic upgrade head` | All migrations apply cleanly |
| `alembic check` | No pending auto-generated migrations |
| Import check | `from main import socket_app` succeeds |
| AI degradation | `get_advisor()` returns `None` when keys are absent |
| Route check | `/chat/ai` endpoint is registered |

### `deploy.yml` — Push to main (after CI passes)

SSH into Droplet → runs `deploy/scripts/deploy.sh`:
1. `git reset --hard origin/main`
2. `pip install -r backend/requirements.txt`
3. `alembic upgrade head`
4. `systemctl restart justadvisor`

---

## Security

- Passwords hashed with **bcrypt** (`passlib`). Pre-hashed passwords are transparently re-hashed on next login.
- No password fields are returned by any `GET` endpoint.
- All user-supplied content is HTML-escaped before DOM insertion (XSS protection throughout the frontend).
- AI API keys are **server-side only** — never sent to the browser.
- TURN credentials are served via `/api/ice-servers`, not hardcoded in frontend source.

---

## Developer

**Ahmad Alyabroudi**  
Computer Science · Jordan University of Science and Technology  
GP2 Graduation Project · Academic Year 2025 / 2026
