# JUST Academic Advisor — CS Chatbot Portal

**Graduation Project 2 (GP2) · Jordan University of Science and Technology**
**Developer:** Ahmad Alyabroudi · Computer Science Department · 2025 / 2026

---

## What This System Is

A full-stack, production-grade web application that acts as an intelligent academic advisor for CS students at JUST. It combines three major technical subsystems into one cohesive platform:

| Subsystem | Technology | Status |
|---|---|---|
| Student Portal & Roadmap | FastAPI + SQLAlchemy + PostgreSQL | Production Ready |
| Real-Time Study Rooms | WebRTC Mesh + Socket.IO + coturn | Production Ready |
| Hybrid AI Chatbot | LangChain + Pinecone + Gemini 1.5 Pro | Production Ready |

---

## Scope Assessment — What Was Built vs. What You Configure

**85% built automatically — 15% requires your manual steps (listed in the checklist at the end of this file).**

| Area | What's Done | What You Do |
|---|---|---|
| Database | SQLAlchemy models, Alembic migrations, PostgreSQL connection pooling, SQLite→PostgreSQL migration script | Create the PostgreSQL database and set the connection string |
| WebRTC | Socket.IO signaling server, peer connection management, ICE relay via coturn config, frontend mesh topology | Provision the Droplet, configure coturn external-ip, create SSL cert |
| AI Chatbot | Full LangChain RAG pipeline, Pinecone queries, Gemini 1.5 Pro integration, source-badge UI, seeding script | Get API keys, create the Pinecone index (dimension 768, cosine), run the seeder |
| Deployment | Nginx config, Gunicorn + UvicornWorker, systemd service, deploy/setup shell scripts | SSH into Droplet, run `initial_setup.sh`, fill `.env` |
| CI/CD | GitHub Actions: PostgreSQL test container, migration checks, import verification, AI graceful-degradation test | Add three GitHub Secrets |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Internet                                  │
│                              │                                      │
│                       ┌──────▼──────┐                              │
│                       │    Nginx    │  HTTPS :443 (TLS via Certbot) │
│                       │  Reverse    │  WebSocket proxy /socket.io/  │
│                       │  Proxy      │  Static files /frontend/      │
│                       └──────┬──────┘                              │
│                              │ :8000 (localhost only)               │
│                       ┌──────▼──────┐                              │
│                       │  Gunicorn   │  1 worker (required for       │
│                       │ +UvicornWkr │  Socket.IO without Redis)     │
│                       └──────┬──────┘                              │
│                    ┌─────────┴──────────┐                          │
│             ┌──────▼──────┐     ┌───────▼──────┐                  │
│             │   FastAPI   │     │  Socket.IO   │                   │
│             │  REST API   │     │  Signaling   │                   │
│             └──────┬──────┘     └──────────────┘                  │
│                    │                                                │
│             ┌──────▼──────┐                                        │
│             │ PostgreSQL  │                                        │
│             └─────────────┘                                        │
│                                                                     │
│  AI Pipeline (per chatbot request):                                 │
│  Question → Google Embeddings → Pinecone Query → Threshold 0.7     │
│           ↓ Score ≥ 0.7               ↓ Score < 0.7               │
│     Gemini In-Context Mode      Gemini General Mode                │
│     "Official Source" badge     "AI-Generated Insight" badge       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- Git

### Steps

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd <repo-folder>

# 2. Create and activate a virtual environment
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install all dependencies (includes AI stack)
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — at minimum, SECRET_KEY is required.
# DATABASE_URL defaults to SQLite if not set.
# AI features are optional for local testing (chatbot falls back to demo mode).

# 5. Run database migrations
alembic upgrade head

# 6. Start the server
#    IMPORTANT: entry point is main:socket_app (not app.py)
uvicorn main:socket_app --reload --port 8000

# 7. Open in browser
#    http://localhost:8000
```

> **Note:** `main:socket_app` wraps FastAPI inside the Socket.IO ASGI layer so both share the same port on `/` and `/socket.io/`.

### Test the AI Chatbot Locally

Without API keys, the chatbot returns helpful demo messages (graceful degradation). To enable full AI:

```bash
# 1. Add keys to .env
GEMINI_API_KEY=your_key_here
PINECONE_API_KEY=your_key_here
PINECONE_INDEX_NAME=just-cs-advisor

# 2. Seed the knowledge base (run once, then re-run if documents change)
python scripts/seed_knowledge_base.py

# 3. Restart the server — AI chatbot is now live
uvicorn main:socket_app --reload --port 8000
```

---

## File Structure

```
GP2 Project Website/
├── .github/
│   └── workflows/
│       ├── ci.yml              # Test on every push (PostgreSQL + import checks)
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
│   │   │   └── student_controller.py   # Login, signup, profile
│   │   ├── core/
│   │   │   ├── ai_advisor.py           # HybridAdvisorChain (LangChain + Pinecone + Gemini)
│   │   │   ├── constants.py            # Shared GRADE_POINTS
│   │   │   ├── database.py             # SQLAlchemy engine (SQLite/PostgreSQL)
│   │   │   └── socket_manager.py       # python-socketio AsyncServer
│   │   ├── models/                     # SQLAlchemy ORM models
│   │   └── schemas/                    # Pydantic validation schemas
│   ├── alembic/
│   │   └── versions/
│   │       ├── 001_initial_schema.py
│   │       ├── 003_add_source_to_chatbot_history.py
│   │       └── ...
│   ├── knowledge_base/
│   │   ├── just_cs_curriculum.txt      # Full CS course catalog with prerequisites
│   │   └── just_regulations.txt        # Graduation rules, GPA, policies, FAQ
│   ├── scripts/
│   │   └── seed_knowledge_base.py      # Embeds .txt files → upserts to Pinecone
│   ├── .env.example
│   ├── main.py                         # App factory + seeding + router registration
│   ├── migrate_sqlite_to_pg.py         # One-time SQLite → PostgreSQL data migration
│   └── requirements.txt
├── deploy/
│   ├── coturn/turnserver.conf
│   ├── gunicorn.conf.py
│   ├── nginx.conf
│   ├── scripts/
│   │   ├── deploy.sh                   # Rolling deploy (git pull, pip, migrate, restart)
│   │   └── initial_setup.sh            # One-time Droplet provisioning
│   └── systemd/justadvisor.service
└── frontend/
    ├── chatbot.html    # Hybrid AI chatbot with Official Source / AI Insight badges
    ├── gpa.html / gpa.js
    ├── index.html      # Login page
    ├── profile.html
    ├── roadmap.html / roadmap.js
    ├── room.html       # WebRTC video/audio/chat room
    ├── signup.html / signup.js
    ├── sidebar.js      # Shared layout: sidebar + auth guard + mini meeting widget
    ├── study-rooms.html
    └── styles.css
```

---

## Environment Variables Reference

All variables are loaded from `backend/.env` (copy from `backend/.env.example`).

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | No | `sqlite:///./Project.db` | Full SQLAlchemy database URL |
| `SECRET_KEY` | Yes | — | Random 32-byte hex secret |
| `ENVIRONMENT` | No | `development` | `development` or `production` |
| `ALLOWED_ORIGINS` | No | `*` | Comma-separated CORS origins |
| `TURN_SERVER_IP` | No | — | Public IP of your coturn Droplet |
| `TURN_USERNAME` | No | — | coturn long-term credential username |
| `TURN_CREDENTIAL` | No | — | coturn long-term credential password |
| `GEMINI_API_KEY` | No* | — | Google AI Studio API key |
| `PINECONE_API_KEY` | No* | — | Pinecone vector database API key |
| `PINECONE_INDEX_NAME` | No | `just-cs-advisor` | Pinecone index name |

*Required for full AI functionality. Without them the chatbot enters demo mode.

```
# PostgreSQL connection string format:
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME

# Generate SECRET_KEY:
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Hybrid AI Chatbot — Architecture Deep Dive

### Decision Pipeline (matches the flowchart)

```
Student Question
       │
       ▼
[1] Google gemini-embedding-001 → query vector (768 dimensions, truncated)
       │
       ▼
[2] Pinecone semantic search → top-3 chunks + similarity scores
       │
       ├─── Score ≥ 0.7 ──────────────────────────────────────────┐
       │                                                           │
       ▼                                                           ▼
[3A] Extract official chunks                              [3B] Flag as General AI
       │                                                           │
       ▼                                                           ▼
[4A] Prompt: "Answer ONLY from                          [4B] Prompt: "Answer as a
     this university data: [chunks]"                         general AI assistant"
       │                                                           │
       ▼                                                           ▼
[5]  Gemini 1.5 Pro In-Context Mode                     Gemini 1.5 Pro General Mode
       │                                                           │
       ▼                                                           ▼
   "Official Source" badge (green)                    "AI-Generated Insight" (amber)
```

### Similarity Threshold

The threshold is set to `0.7` in `backend/app/core/ai_advisor.py`:
```python
SIMILARITY_THRESHOLD = 0.7
```
Increase this (e.g. 0.75) for stricter official-only answers. Decrease (e.g. 0.65) for broader context retrieval.

### Adding More Knowledge to Pinecone

1. Place any `.txt` file inside `backend/knowledge_base/`
2. Run: `python scripts/seed_knowledge_base.py`
3. The script chunks, embeds, and upserts — no code changes needed

---

## Database

### Local (SQLite — development)

Default — no setup needed. `Project.db` is created automatically on first run.

### Production (PostgreSQL)

```bash
# On Droplet, after setting DATABASE_URL in .env:
cd /var/www/justadvisor/backend
../venv/bin/alembic upgrade head
```

### SQLite → PostgreSQL Migration

```bash
# Export existing data from SQLite and import into PostgreSQL:
SQLITE_PATH=/path/to/Project.db python migrate_sqlite_to_pg.py
```

---

## API Endpoints

Full interactive documentation: `https://yourdomain.com/docs`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/login` | Student login (form data) |
| `POST` | `/signup` | Student registration (verified email required) |
| `GET` | `/student/{id}` | Get student profile |
| `PUT` | `/student/{id}` | Update name/phone |
| `PUT` | `/student/{id}/password` | Change password |
| `GET` | `/roadmap/{id}` | Get roadmap with grades |
| `GET` | `/roadmap/{id}/sync-stats` | Recalculate and return credit counts |
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
| `POST` | `/chat/ai` | **Hybrid RAG AI chatbot** |

---

## Socket.IO Real-Time Events

### Client → Server

| Event | Payload | Description |
|---|---|---|
| `join_room` | `{roomId, userId, name}` | Join a study room |
| `leave_room` | `{roomId, userId}` | Leave a study room |
| `offer` | `{target, sdp}` | WebRTC SDP offer to peer |
| `answer` | `{target, sdp}` | WebRTC SDP answer to peer |
| `ice_candidate` | `{target, candidate}` | Relay ICE candidate |
| `send_message` | `{roomId, userId, name, message}` | Chat message to room |
| `join_lobby` | `{}` | Subscribe to room-list updates |
| `leave_lobby` | `{}` | Unsubscribe from lobby |
| `room_created` | `{}` | Notify lobby of new room |

### Server → Client

| Event | Payload | Description |
|---|---|---|
| `existing-users` | `[{sid, userId, name}]` | Current room members sent to joiner |
| `user-joined` | `{sid, userId, name}` | New participant joined |
| `user-left` | `{sid, userId}` | Participant disconnected |
| `member-count` | `{count}` | Updated headcount |
| `offer` / `answer` | `{from, sdp}` | Relayed SDP |
| `ice-candidate` | `{from, candidate}` | Relayed ICE candidate |
| `receive-message` | `{userId, name, message, timestamp}` | Chat broadcast |
| `room-list-updated` | `{}` | Lobby refresh trigger |

---

## CI/CD Pipeline

### `ci.yml` — Runs on every push and every PR to main

| Step | What it checks |
|---|---|
| PostgreSQL service container | Real DB for migration tests |
| `alembic upgrade head` | All migrations apply cleanly |
| `alembic check` | No unapplied auto-generated migrations |
| Import check | `from main import socket_app` succeeds |
| AI degradation check | `get_advisor()` returns `None` when keys are absent |
| Chatbot route check | `/ai` endpoint is registered |

### `deploy.yml` — Runs on push to main

SSH into the Droplet and executes `deploy/scripts/deploy.sh`:
1. `git reset --hard origin/main`
2. `pip install -r backend/requirements.txt`
3. `alembic upgrade head`
4. `systemctl restart justadvisor`

### Required GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|---|---|
| `DROPLET_HOST` | Public IP of your DigitalOcean Droplet |
| `DROPLET_USER` | SSH username (e.g. `root`) |
| `SSH_PRIVATE_KEY` | Contents of your SSH private key file |

---

## Security Notes

- Passwords are hashed with **bcrypt** (`passlib`). Plaintext passwords stored before this version are transparently re-hashed on next login.
- The `GET /students` endpoint returns no password fields.
- All user-supplied content is HTML-escaped before being inserted into the DOM (XSS protection in all frontend files).
- AI API keys (`GEMINI_API_KEY`, `PINECONE_API_KEY`) are **server-side only** — never exposed to the browser.
- TURN credentials are served via `/api/ice-servers` endpoint, not hardcoded in frontend source.

---

## Manual Deployment Checklist (Your 15%)

Complete these steps in order to bring the system fully operational on DigitalOcean.

### Phase 1 — External Accounts & API Keys

- [ ] **1. Get a Google Gemini API key**
  - Go to [Google AI Studio](https://aistudio.google.com/app/apikey) → Create API Key
  - Save as `GEMINI_API_KEY` in your Droplet's `.env`

- [ ] **2. Get a Pinecone account and API key**
  - Register at [pinecone.io](https://www.pinecone.io) → API Keys → Create Key
  - Save as `PINECONE_API_KEY` in your Droplet's `.env`

- [ ] **3. Create the Pinecone index**
  - In the Pinecone console: **Create Index**
  - Name: `just-cs-advisor`
  - Dimensions: **768** (Google `gemini-embedding-001` with `output_dimensionality=768`)
  - Metric: **cosine**
  - Type: **Serverless** (AWS us-east-1 or nearest region)
  - Save the index name as `PINECONE_INDEX_NAME` in `.env`

### Phase 2 — DigitalOcean Infrastructure

- [ ] **4. Create a DigitalOcean Droplet**
  - Ubuntu 22.04 LTS, minimum 2 GB RAM / 1 vCPU
  - Enable your SSH public key during creation

- [ ] **5. Point your domain to the Droplet**
  - DNS A record: `yourdomain.com` → `<Droplet IP>`
  - DNS A record: `www.yourdomain.com` → `<Droplet IP>`
  - Wait for DNS propagation

- [ ] **6. Provision the server**
  - Edit `deploy/scripts/initial_setup.sh`: set `REPO_URL` and `DOMAIN`
  - SSH into the Droplet as root: `bash initial_setup.sh`

### Phase 3 — Configuration on the Droplet

- [ ] **7. Fill in `backend/.env` on the Droplet**
  ```bash
  nano /var/www/justadvisor/backend/.env
  ```
  Set at minimum:
  ```
  DATABASE_URL=postgresql://...
  SECRET_KEY=<32-byte hex>
  GEMINI_API_KEY=<from step 1>
  PINECONE_API_KEY=<from step 2>
  PINECONE_INDEX_NAME=just-cs-advisor
  ALLOWED_ORIGINS=https://yourdomain.com
  ```

- [ ] **8. Set coturn external IP**
  ```bash
  nano /etc/turnserver.conf
  # Set: external-ip=<Droplet public IP>
  systemctl restart coturn
  ```

- [ ] **9. Verify SSL certificate**
  ```bash
  certbot certificates
  # Confirm https://yourdomain.com loads without warnings
  ```

### Phase 4 — AI Knowledge Base Seeding

- [ ] **10. Run the Pinecone seeder**
  ```bash
  cd /var/www/justadvisor/backend
  ../venv/bin/python scripts/seed_knowledge_base.py
  ```
  Expected output: `Seeding complete! Total vectors in index: ~150`

- [ ] **11. (Optional) Add your own documents to the knowledge base**
  - Place `.txt` files in `backend/knowledge_base/`
  - Re-run the seeder — it upserts idempotently (duplicate IDs are overwritten)

- [ ] **12. Seed the student verification table**
  ```sql
  -- Via psql or any PostgreSQL client:
  INSERT INTO student_verification (email, university_id)
  VALUES ('student@cit.just.edu.jo', '202212345');
  ```

### Phase 5 — Activate CI/CD

- [ ] **13. Add GitHub Secrets**
  - Go to your GitHub repo → Settings → Secrets and variables → Actions
  - Add: `DROPLET_HOST`, `DROPLET_USER`, `SSH_PRIVATE_KEY`

- [ ] **14. Trigger a test deployment**
  - Push any change to `main` and watch the Actions tab
  - Both `CI – Lint & Test` and `Deploy to DigitalOcean` must pass ✅

### Phase 6 — End-to-End Verification

- [ ] **15. Full system smoke test**
  - [ ] Sign up with a verified email/university_id pair
  - [ ] Log in and verify the roadmap shows grades on completed courses
  - [ ] Ask the chatbot: *"What is the prerequisite for CS375?"*
    - Should show green **Official Source** badge
  - [ ] Ask: *"How do I prepare for a software engineering interview?"*
    - Should show amber **AI-Generated Insight** badge
  - [ ] Open two browser tabs/devices, create a study room, join from the other
  - [ ] Verify video, audio, and chat work
  - [ ] Test from two different network connections to verify TURN relay works

---

## Developer

**Ahmad Alyabroudi**
Computer Science — Jordan University of Science and Technology
GP2 Graduation Project · Academic Year 2025 / 2026

*All rights reserved.*
