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
| **Frontend** | Next.js 15 (App Router), TypeScript, Tailwind CSS, Framer Motion |
| **LLM** | OpenRouter (`deepseek/deepseek-r1`), token streaming via SSE |
| **RAG** | ChromaDB with `intfloat/multilingual-e5-base` embeddings |
| **Infra** | Docker Compose, Proxmox/CasaOS, MikroTik |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- [pnpm](https://pnpm.io)

### 1. Clone & Configure

```bash
git clone https://github.com/anomalyco/PEMALI.git
cd PEMALI
```

Create `config/.env`:

```env
OPENROUTER_KEY=sk-or-v1-...
DATABASE_URL=postgresql://pemali:pemali@localhost:5432/pemali
CHROMA_HOST=localhost
CHROMA_PORT=8200
```

### 2. Database & Containers

```bash
cd infra
docker compose up -d    # starts PostgreSQL + ChromaDB
```

### 3. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Worker (separate terminal)

```bash
cd backend
source venv/bin/activate
python worker.py
```

### 5. Frontend

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
│   │   ├── orchestrator.py      # 4-phase pipeline (1108 lines)
│   │   ├── registry.py          # Module auto-discovery + execution
│   │   ├── models.py            # Pydantic schemas, TelemetryEvent
│   │   ├── telemetry.py         # SSE event emitter
│   │   ├── session_logger.py    # Per-session audit log (raw JSON)
│   │   ├── llm_client.py        # OpenRouter LLM client
│   │   ├── memory.py            # ChromaDB + knowledge graph queries
│   │   └── memory_processor.py  # TemporalPatternExtractor + KnowledgeGraphBuilder
│   ├── agents/
│   │   ├── base_agent.py        # Retry logic, self-correction
│   │   ├── manager_agent.py     # DAG planner
│   │   └── sub_agents/          # auditor, scheduler, etc.
│   ├── modules/                 # UTI V2 tools (auto-discovered)
│   ├── schemas/                 # Pydantic models per route
│   ├── tests/                   # 48 test suite
│   └── logs/sessions/           # Per-session audit logs (auto-cleaned)
│
├── frontend/
│   └── src/
│       ├── app/dashboard/       # Main dashboard page
│       ├── components/pemali/   # All custom components
│       │   └── dashboard/       # ObservationZone, InteractionZone
│       ├── stores/              # Zustand state management
│       ├── lib/                 # TypeScript types, utils, phase logic
│       └── styles/              # globals.css (design tokens)
│
├── infra/                       # Docker Compose configs
├── config/                      # Environment variables
└── docs/                        # Architecture & sprint specs
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
- **Session Logging** — Per-session raw JSON telemetry logs with auto-cleanup
- **Chat Interface** — Live markdown formatting, fade transitions between pipeline phases
- **Dark Terminal Aesthetic** — Anthropic-inspired control room dashboard

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/stream` | Trigger audit + SSE telemetry stream |
| `GET`  | `/api/telemetry` | SSE stream for dashboard |
| `GET`  | `/api/tasks` | List autonomous tasks |
| `GET`  | `/api/health` | Health check |

---

## Testing

```bash
cd backend
source venv/bin/activate
pytest tests/ -v

# 48 tests covering:
#   DAG stress tests, cognitive memory, cognitive pattern extraction,
#   gempa module, tool scoping, dashboard pipeline
```

---

## Development

### Coding Standards

- **TypeScript**: strict mode, Zustand for state, Framer Motion for animations
- **Python**: type hints on all function signatures, Black formatter
- **Commit format**: `feat(scope): description` | `fix(scope): description`

### Module Development

Create a new file in `backend/modules/` inheriting `PemaliModuleV2`:

```python
from backend.core.base_module import PemaliModuleV2, ModuleOutput
from pydantic import BaseModel

class MyInput(BaseModel):
    location: str
    metric: str = "ndvi"

class MyModule(PemaliModuleV2):
    name = "my_module"
    description = "Custom environmental sensor"
    input_schema = MyInput

    async def execute(self, params: MyInput, context: dict) -> ModuleOutput:
        return ModuleOutput(status=200, data={"result": "ok"})
```

Modules are auto-discovered on startup — no registry edits needed.

---

## Sprint Progress

| Sprint | Status | Highlights |
|--------|--------|-----------|
| Sprint 1 (Stabilization) | ✅ | ErrorResponse, execute_with_safety, scoped registry, DAG tests (20/20) |
| Sprint 2 (Cognitive Memory) | ✅ | TemporalPatternExtractor, KnowledgeGraphBuilder, MemoryNode/MemoryEdge (15/15) |
| Sprint 3 (Narrative + SDUI) | ✅ | SSE telemetry, narrative stream, server-driven UI |
| Sprint 4 (Phase Pipeline) | ✅ | 4-phase pipeline, validation + re-spawn, chat interface |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENROUTER_KEY` | Yes | — | OpenRouter API key |
| `OPENROUTER_MODEL` | No | `deepseek/deepseek-r1` | LLM model |
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `CHROMA_HOST` | No | `localhost` | ChromaDB host |
| `CHROMA_PORT` | No | `8200` | ChromaDB port |
| `WORKER_POLL_INTERVAL` | No | `10` | Worker poll interval (seconds) |

---

## License

MIT

---

<p align="center">
  <sub>Built for <strong>Festival Pelajar Ajeg Bali Ke-4 2026</strong></sub><br/>
  <sub>Digital Manuscript for Environmental Sovereignty · <i>Parahyangan · Pawongan · Palemahan</i></sub>
</p>
