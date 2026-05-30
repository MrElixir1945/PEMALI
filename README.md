# PEMALI

<p align="center">
  <strong>Programmable Entity for Multi-Agent Logical Inference</strong><br/>
  Autonomous Environmental Audit Platform · Bali, Indonesia
</p>

---

## What is PEMALI?

PEMALI is an autonomous multi-agent audit system for environmental monitoring in Bali. Built on the philosophy of **Tri Hita Karana** (THK) — the Balinese principle of harmony between spirit, people, and nature — the system serves as an early-warning digital "Pemali" (traditional prohibition) that safeguards Bali's ecological balance.

A single user prompt triggers a 4-phase pipeline (Planning → Execute → Validate → Synthesis) where specialized agents independently investigate satellite data, water quality, fire risks, and public intelligence — then synthesize their findings into a comprehensive audit report.

---

## Architecture

```
User Prompt
    ↓
Manager Agent ── Plans DAG, delegates tasks, synthesizes reports
    ↓
Sub-Agents ──── geo_agent, water_agent, fire_agent, osint_agent, scheduler_agent
    ↓
Module Registry ── zero-narrative sensors (mock, satellite, scheduler)
    ↓
PostgreSQL + ChromaDB ── state, history, RAG, knowledge graph
    ↓
SSE /api/stream ── real-time streaming to frontend
```

### 4-Phase Pipeline

| Phase | Description |
|-------|-------------|
| **Planning** | Manager analyzes the request, assembles an agent team, builds a DAG |
| **Execute** | Sub-agents run in parallel, calling tools via module registry |
| **Validate** | Anomaly detection, retry logic, re-spawn failed agents up to 2× |
| **Synthesis** | All results merged into a comprehensive environmental report |

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, Pydantic v2, PostgreSQL, ChromaDB, asyncio |
| **Frontend** | Next.js 16 (App Router), TypeScript, Tailwind CSS, Framer Motion |
| **LLM** | OpenRouter (`deepseek-v4-flash`), token streaming via SSE |
| **RAG** | ChromaDB with `paraphrase-multilingual-MiniLM-L12-v2` embeddings |
| **Infra** | Docker Compose, CasaOS, Cloudflare Zero Trust |

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- [pnpm](https://pnpm.io)

### 1. Clone & Configure

```bash
git clone https://github.com/MrElixir1945/PEMALI.git
cd PEMALI
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# isi OPENROUTER_KEY dan DATABASE_URL di .env
uvicorn backend.main:app --reload --port 8080
```

### 3. Worker (separate terminal)

```bash
cd backend
source .venv/bin/activate
python worker.py
```

### 4. Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Open **http://localhost:3000/dashboard**

---

## Project Structure

```
pemali/
├── backend/
│   ├── main.py                  # FastAPI entry + SSE endpoints
│   ├── worker.py                # Autonomous task tick engine
│   ├── core/
│   │   ├── orchestrator.py      # 4-phase pipeline
│   │   ├── registry.py          # Module auto-discovery + execution
│   │   ├── models.py            # Pydantic schemas, TelemetryEvent
│   │   ├── telemetry.py         # SSE event emitter
│   │   ├── session_logger.py    # Per-session audit log (raw JSON)
│   │   ├── llm_client.py        # OpenRouter LLM client
│   │   ├── memory.py            # ChromaDB + knowledge graph queries
│   │   ├── memory_processor.py  # TemporalPatternExtractor + KnowledgeGraphBuilder
│   │   └── database.py          # SQLAlchemy models
│   ├── modules/                 # UTI V2 tools (auto-discovered)
│   ├── tests/                   # Test suite
│   └── docs/README.md           # Full documentation
│
├── frontend/
│   └── src/
│       ├── app/dashboard/       # Main dashboard page
│       ├── components/pemali/   # All custom components
│       ├── stores/              # Zustand state management
│       └── lib/                 # TypeScript types, utils
│
├── Dockerfile.backend           # Python/FastAPI container
├── Dockerfile.frontend          # Next.js production container
├── docker-compose.yml           # Full deployment orchestration
└── cloudflare/                  # Cloudflare Tunnel config
```

---

## Features

- **Autonomous Multi-Agent Audits** — Single natural language prompt triggers 5+ specialized agents
- **DAG-based Task Orchestration** — Tasks can run parallel or sequential based on dependencies
- **Self-Healing Pipeline** — Agents retry failed tool calls up to 3×; validation phase re-spawns failed agents
- **Real-Time SSE Streaming** — Token-by-token LLM output, agent state transitions, live progress
- **4-Phase Report Pipeline** — Planning → Execute → Validate → Synthesis → Done
- **RAG Memory** — Long-term semantic storage in ChromaDB for historical audit comparison
- **Cognitive Memory** — Temporal pattern extraction + knowledge graph construction
- **Chat Interface** — Live markdown formatting, fade transitions between pipeline phases
- **Dark Terminal Aesthetic** — Anthropic-inspired control room dashboard

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/stream` | Trigger audit + SSE telemetry stream |
| `GET`  | `/api/telemetry` | SSE stream for dashboard |
| `GET`  | `/api/status` | System status |
| `GET`  | `/api/sessions` | List chat sessions |
| `GET`  | `/api/history/{id}` | Session history |
| `GET`  | `/api/tasks` | List autonomous tasks |
| `GET`  | `/api/laporan` | Audit reports |
| `POST` | `/api/trigger` | Manual audit trigger |

---

## Testing

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENROUTER_KEY` | Yes | — | OpenRouter API key |
| `OPENROUTER_MODEL` | No | `deepseek/deepseek-v4-flash:free` | LLM model |
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `CHROMA_PATH` | No | `./chroma_db` | ChromaDB persistent path |
| `BACKEND_URL` | No | `http://backend:8080` | Internal backend URL |
| `TUNNEL_TOKEN` | Yes* | — | Cloudflare Tunnel token |

---

## 🚀 Deployment Guide (Home Server + Cloudflare Zero Trust)

Panduan ini untuk deploy PEMALI di home server (CasaOS/Linux) dan expose ke public via Cloudflare Zero Trust Tunnel.

### Prasyarat Server

- **Docker** & **Docker Compose** terinstall
- **cloudflared** terinstall (`sudo apt install cloudflared` atau download dari Cloudflare)
- **Domain** yang di-manage Cloudflare (bisa pakai subdomain)
- **OpenRouter API Key** (daftar di https://openrouter.ai)

### Arsitektur Deployment

```
Browser → https://domain.com
              ↓
    Cloudflare Edge (CDN + Proxy)
              ↓
    Cloudflare Tunnel (cloudflared)
              ↓
    Docker Container: frontend (:3000)
              ↓  (proxy /api/* via Next.js rewrites)
    Docker Container: backend (:8080)
              ↓
    Docker Container: db (:5432)
              ↓
    Docker Container: worker (background)
```

### Step-by-Step

#### 1. Clone Branch deploy-v2

```bash
git clone -b deploy-v2 https://github.com/MrElixir1945/PEMALI.git
cd PEMALI
```

Atau kalo repo udah ada:

```bash
cd /path/to/PEMALI
git fetch origin
git checkout deploy-v2
git pull origin deploy-v2
```

#### 2. Setup Environment Variables

```bash
cp backend/.env.example .env
nano .env
```

Isi file `.env`:

```env
DATABASE_URL=postgresql://admin:pemalipass@db:5432/pemali_db
CHROMA_PATH=/app/chroma_db
BACKEND_URL=http://backend:8080
OPENROUTER_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_MODEL=deepseek/deepseek-v4-flash:free
TUNNEL_TOKEN=
```

> **OPENROUTER_KEY**: isi dengan API key dari OpenRouter
> **TUNNEL_TOKEN**: kosongin dulu, nanti diisi setelah setup tunnel

#### 3. Setup Cloudflare Tunnel (Sekali Seumur Hidup)

```bash
# Login ke Cloudflare
cloudflared tunnel login

# Buat tunnel baru
cloudflared tunnel create pemali-tunnel
```

Output akan muncul seperti ini:

```
Created tunnel pemali-tunnel with id xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Credentials file saved to: /root/.cloudflared/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.json
Tunnel credentials: eyJhIjoi... (TOKEN INI)
```

**Copy token** (string panjang setelah "Tunnel credentials:") dan paste ke `.env`:

```bash
nano .env
# TUNNEL_TOKEN=eyJhIjoi... (paste di sini)
```

#### 4. Route DNS ke Tunnel

```bash
cloudflared tunnel route dns pemali-tunnel subdomain.domain.com
```

Contoh:

```bash
cloudflared tunnel route dns pemali-tunnel pemali.example.com
```

#### 5. Build & Jalankan Semua Service

```bash
docker compose up -d --build
```

Proses build akan memakan waktu 5-15 menit (tergantung koneksi) karena:
- Download Python dependencies (sentence-transformers ~500MB)
- Download pnpm packages (Next.js, React, dll)
- Pre-load embedding model untuk ChromaDB

#### 6. Verifikasi

```bash
# Cek status container
docker compose ps
```

Harusnya keliatan 5 container:

| Container | Status | Port |
|-----------|--------|------|
| `pemali_db` | running | 5432 |
| `pemali_backend` | running | 8080 |
| `pemali_worker` | running | — |
| `pemali_frontend` | running | 3000 |
| `pemali_tunnel` | running | — |

#### 7. Akses

- **Local**: `http://localhost:3000`
- **Public**: `https://subdomain.domain.com`

### Docker Services Detail

| Service | Image | Fungsi |
|---------|-------|--------|
| `db` | postgres:15 | Database PostgreSQL |
| `backend` | custom (Dockerfile.backend) | FastAPI server |
| `worker` | custom (Dockerfile.backend) | Background task processor |
| `frontend` | custom (Dockerfile.frontend) | Next.js UI |
| `tunnel` | cloudflare/cloudflared | Cloudflare Zero Trust Tunnel |

### Perintah Penting

```bash
# Start semua service
docker compose up -d

# Stop semua service
docker compose down

# Restart service tertentu
docker compose restart backend

# Lihat log
docker compose logs -f backend
docker compose logs -f frontend

# Build ulang (setelah update kode)
docker compose up -d --build

# Bersihin container + volume (HAPUS DATA)
docker compose down -v
```

### Troubleshooting

**Build gagal karena `Input/output error`:**
```bash
# Cek disk space
df -h

# Bersihin docker cache
docker system prune -af

# Rebuild
docker compose up -d --build
```

**Frontend tidak bisa connect ke backend:**
```bash
# Cek log backend
docker compose logs backend

# Cek apakah backend bisa diakses dari frontend
docker compose exec frontend wget -qO- http://backend:8080/api/status
```

**Tunnel error / tidak bisa akses public:**
```bash
# Cek log tunnel
docker compose logs tunnel

# Verifikasi tunnel token
echo $TUNNEL_TOKEN

# Test tunnel manual (diluar docker)
cloudflared tunnel run pemali-tunnel
```

**Database connection error:**
```bash
# Cek log database
docker compose logs db

# Pastikan DATABASE_URL di .env menggunakan hostname "db" (bukan localhost)
# Contoh: postgresql://admin:pemalipass@db:5432/pemali_db
```

### Update ke Versi Terbaru

```bash
cd /path/to/PEMALI
git pull origin deploy-v2
docker compose up -d --build
```

---

## License

GNU General Public License v3.0 (GPLv3)

---

<p align="center">
  <sub>Built for <strong>Festival Pelajar Ajeg Bali Ke-4 2026</strong></sub><br/>
  <sub>Digital Manuscript for Environmental Sovereignty · <i>Parahyangan · Pawongan · Palemahan</i></sub>
</p>
