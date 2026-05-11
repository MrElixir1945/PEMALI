# PEMALI V2 — AGENTS.md
# Programmable Entity for Multi-Agent Logical Inference

## Project overview

PEMALI (Platform Ekologi Modular Agentic berbasis Artificial Intelligence) adalah
autonomous super-agent framework yang dibangun untuk Festival Pelajar Ajeg Bali Ke-4 2026.
Sistem ini mengadopsi nilai "Pemali" (pantangan adat) sebagai sistem peringatan dini
digital yang menjaga keseimbangan alam Bali, beroperasi berdasarkan filosofi
**Tri Hita Karana (THK)** untuk memastikan teknologi selaras dengan kearifan lokal.

THK Alignment:
- **Parahyangan**: Hubungan dengan Tuhan (keseimbangan spiritual dalam audit)
- **Pawongan**: Hubungan dengan sesama (kolaborasi antar agent, transparansi)
- **Palemahan**: Hubungan dengan alam (fokus pada lingkungan Bali)

Stack singkat:
- Backend  → FastAPI, Pydantic, ChromaDB, PostgreSQL, asyncio
- Frontend → Next.js 15 (App Router), TypeScript, Tailwind CSS, Framer Motion
- Infra    → Docker Compose, Proxmox/CasaOS, MikroTik (home server)
- LLM API  → OpenRouter (`deepseek/deepseek-r1` default, swappable)

---

## Architecture (baca sebelum sentuh kode apapun)
User Prompt
↓
Manager Agent          ← system prompt dengan NARRATIVE CONTRACT + RAG context
↓ (delegates via DAG, emit TelemetryEvent ke SSE)
Sub-Agents             ← auditor_agent, scheduler_agent, dst (NARRATIVE CONTRACT + state machine)
↓ (call tools, track duration_ms via time.monotonic())
Module Registry        ← zero-narrative sensors, return raw JSON dengan metadata
↓
PostgreSQL + ChromaDB  ← state, history, RAG memory, knowledge graph (MemoryNode/MemoryEdge)
│
├→ SSE /api/telemetry  ← real-time stream ke frontend (TelemetryEvent + metadata)
│       ↓
│   NarrativeStream    ← SSE consumer, feed ke Zustand store
│       ↓
│   Frontend Dashboard ← DAGViewer, NarrativeCard, TelemetryFeed (semua baca dari store)
│
↑
Worker Daemon          ← tick engine, poll autonomous_tasks, no human trigger
↑
Cognitive Memory       ← TemporalPatternExtractor + KnowledgeGraphBuilder (Sprint 2)

DAG = Directed Acyclic Graph. Dependensi task antar sub-agent bisa paralel
atau sekuensial. Manager TIDAK langsung answer — ia plan dulu, lalu delegate.
SSE telemetry dikirim setiap kali agent ganti state (THINKING/EXECUTING/DONE/ERROR).

---

## Backend rules

### Module / Tool standard (UTI V2)
- Setiap modul inherit dari `PemaliModule` base class.
- Modul adalah SENSOR MURNI. Return value wajib sesuai schema UTI:
  ```
  {
    "status": "success" | "error",
    "data": {...},           // raw technical data
    "agent_hint": "...",     // brief explanation for AI understanding
    "thk_alignment": {       // alignment with Tri Hita Karana
      "parahyangan": "...", // spiritual balance aspect
      "pawongan": "...",    // social collaboration aspect
      "palemahan": "..."    // environmental aspect
    }
  }
  ```
- Semua input modul divalidasi Pydantic sebelum eksekusi. Hard fail jika
  schema tidak match — jangan silent ignore.
- Modul baru: buat file di `modules/`, definisikan Pydantic schema, gunakan
  `async def execute`. Auto-discovery via importlib scan.
- Sanitasi input OSINT untuk mencegah code injection.
- Jangan modifikasi `registry.py` secara manual untuk tiap modul baru.

### Self-correction pattern
- Sub-agent yang dapat error 4xx/5xx dari tool HARUS re-read error message,
  adjust parameter, dan retry maksimal 3x sebelum report ke Manager.
- Retry logic ada di `base_agent.py`. Jangan duplikasi di sub-agent lain.

### RAG / Memory
- **Short-term (Context)**: Menyimpan variabel dari langkah sebelumnya (misal:
  koordinat wilayah) agar modul selanjutnya bisa langsung bekerja.
- **Long-term (Historical)**: Menyimpan database audit masa lalu untuk
  perbandingan tren kerusakan di PostgreSQL.
- **Semantic (Vector)**: ChromaDB untuk tanya-jawab dengan histori audit.
  - Collection naming: `pemali_{agent_name}_{topic}` (lowercase, underscores).
  - Embedding model: `intfloat/multilingual-e5-base` — JANGAN ganti tanpa
    migration. Bahasa Indonesia adalah first-class citizen di sini.
  - Query ke ChromaDB selalu lewat `core/memory.py` → `query_semantic()`, bukan langsung client.
  - RAG context masuk sebagai raw text ke system prompt Manager Agent, dengan instruksi
    cara membaca: identifikasi lokasi, bandingkan kondisi, prioritaskan tren memburuk,
    gunakan sebagai baseline.
- Simpan hasil task ke ChromaDB hanya setelah task STATUS = COMPLETE.
- **Cognitive Memory (Sprint 2)**: `TemporalPatternExtractor` + `KnowledgeGraphBuilder`
  untuk ekstrak pola temporal dan bangun relasi entity di PostgreSQL (`memory_nodes`, `memory_edges`).

### Worker Daemon
- `worker.py` adalah background process terpisah. Jangan import langsung dari
  FastAPI main app.
- Poll interval default: 10s. Configurable via `WORKER_POLL_INTERVAL` env var.
- Tabel yang dimonitor: `autonomous_tasks`. Schema:
  `(id, agent_name, payload JSON, scheduled_at, status, retries, last_error)`.
- Status lifecycle: PENDING → RUNNING → COMPLETE | FAILED.
- Jangan hapus row FAILED — flag saja, biarkan untuk audit trail.

### API routes
- `/api/trigger`   POST  → terima instruksi user, spawn Manager Agent session
- `/api/telemetry` GET   → SSE stream untuk Observation Zone
- `/api/tasks`     GET   → list autonomous_tasks (dengan filter status)
- Route baru → wajib ada schema Pydantic di `schemas/` dan docstring singkat.

### Autonomous Reasoning Loop
1. **Trigger**: Perubahan data satelit atau jadwal rutin memicu agent.
2. **Reasoning**: Agent menganalisis data awal dan menentukan alat (module) mana
   yang dibutuhkan.
3. **Action**: Agent mengirim JSON call melalui Communicate Layer.
4. **Observation**: Agent menerima hasil, memperbarui memori, dan memutuskan
   apakah audit selesai atau butuh modul tambahan.

---

## Frontend rules (BACA SEMUA SEBELUM NULIS KOMPONEN APAPUN)

### Aesthetic direction — "Anthropic Terminal"
Satu arah desain, tidak boleh menyimpang:
- TONE     : Precision intelligence. Clean, dark-capable, editorial.
              Bukan SaaS template. Bukan landing page startup. Ini control room.
- FEEL     : Claude.ai meets terminal. Whitespace agresif. Typography kuat.
              Setiap elemen punya purpose — tidak ada dekorasi gratisan.
- VIBE REF : Anthropic Console + Linear app + Vercel Dashboard (bukan Notion,
              bukan Shadcn default, bukan Tailwind template gallery)

### Typography
- Display / heading  : "Geist" atau "DM Mono" (monospace untuk agent output)
- Body               : "Geist Sans" atau system-ui sebagai fallback
- DILARANG           : Inter, Roboto, Arial, Poppins, nunito
- Size scale         : 13px (mono labels), 14px (body), 16px (ui), 20px (h3),
                       28px (h2), 40px+ (hero)
- Weight             : 400 (body), 500 (ui medium), semibold HANYA untuk
                       status badges dan agent names

### Color system (CSS variables — semua di `globals.css`)
```css
/* PEMALI Color tokens */
--pemali-bg          : #0A0A0B;   /* near-black canvas */
--pemali-surface     : #111113;   /* card / panel bg */
--pemali-border      : rgba(255,255,255,0.08);
--pemali-border-glow : rgba(139,92,246,0.3);  /* purple accent border */

--pemali-text-primary   : #F4F4F5;
--pemali-text-secondary : #A1A1AA;
--pemali-text-muted     : #52525B;

/* Agent state colors */
--state-thinking   : #8B5CF6;   /* purple */
--state-spawning   : #3B82F6;   /* blue */
--state-executing  : #10B981;   /* emerald */
--state-error      : #EF4444;   /* red */
--state-complete   : #6EE7B7;   /* light emerald */

/* Accent */
--pemali-accent    : #8B5CF6;   /* purple, satu-satunya accent color */
```

DILARANG:
- Purple gradient on white (classic AI slop)
- Blue + teal SaaS combo
- Card dengan drop-shadow tebal
- Hero section dengan centered text + CTA button besar
- Warna background putih (#FFF) di halaman utama

### Layout: dua zona fungsional
┌─────────────────────────────────────────────────┐
│  OBSERVATION ZONE          │  INTERACTION ZONE  │
│  (60% lebar)               │  (40% lebar)      │
│                            │                    │
│  • DAG visualizer          │  • Chat input      │
│  • Agent state timeline    │  • Task history    │
│  • SSE telemetry stream    │  • Trigger button │
│  • Module output cards     │                    │
└─────────────────────────────────────────────────┘
- Di mobile: stack vertikal, Interaction Zone di atas.
- Split bisa di-resize (drag handle). Default 60/40.
- Tidak ada topbar/navbar klasik — hanya slim status bar di atas
  yang show: model aktif | worker status | last tick timestamp.

### Component conventions
- Semua komponen di `components/pemali/`. Bukan `components/ui/`.
- Gunakan `cn()` util dari `clsx` + `tailwind-merge`.
- Server Components default. Client hanya kalau ada interactivity (SSE,
  drag, real-time update).
- `AgentCard.tsx`     : tampilkan satu agent + statusnya
- `TelemetryFeed.tsx` : SSE consumer, render state timeline
- `DagViewer.tsx`     : visualisasi DAG (SVG manual + Tailwind)
- `NarrativeStream.tsx` : SSE → Zustand store bridge (invisible component)
- `NarrativeCard.tsx` : render narasi agent per-event (state-coded timeline)
- `ModuleOutput.tsx`  : render JSON output modul dengan syntax highlight
- `ChatInput.tsx`     : textarea + kirim ke /api/trigger
- Tidak ada shadcn/ui default component tanpa kustomisasi warna ke design
  token PEMALI dulu.

### Animation
- Library: Framer Motion untuk semua transisi utama.
- Agent state badge: animate warna sesuai `--state-*` token.
- Telemetry feed: new item slide-in dari bawah, fade-out item lama.
- DAG node: pulse subtle saat status RUNNING.
- Page load: staggered reveal (0.05s delay per komponen utama).
- DILARANG: bounce, spin terus-terusan, atau animasi yang ganggu reading.

### SSE / Real-time pattern
```typescript
// Pattern standar untuk SSE di PEMALI
useEffect(() => {
  const es = new EventSource('/api/telemetry')
  es.onmessage = (e) => {
    const event = JSON.parse(e.data) // { type, agent, payload, ts }
    dispatch({ type: 'ADD_EVENT', payload: event })
  }
  return () => es.close()
}, [])
```
- State SSE di Zustand store (`stores/telemetryStore.ts`).
- Max buffer di frontend: 200 events. Older events di-trim dari head.

### Server-Driven UI (SDUI)
- Backend boleh return `{ render_as: "table" | "map" | "chart" | "raw" }`
  di dalam payload modul.
- `ModuleOutput.tsx` harus handle semua tipe render di atas.
- Frontend adalah DUMB CLIENT — tidak boleh hardcode asumsi bentuk data.

---

## File structure
pemali/
├── backend/
│   ├── main.py               # FastAPI entry point
│   ├── agents/
│   │   ├── base_agent.py     # retry logic, self-correction
│   │   ├── manager_agent.py  # DAG planner
│   │   └── sub_agents/       # auditor, scheduler, dst
│   ├── modules/              # UTI V2 tools (zero-narrative)
│   ├── registry.py           # auto-discovery
│   ├── rag_service.py        # ChromaDB wrapper
│   ├── worker.py             # tick engine daemon
│   └── schemas/              # Pydantic models per route
│
└── frontend/
├── app/
│   ├── page.tsx           # root — dua zona layout
│   └── api/
│       ├── trigger/route.ts
│       └── telemetry/route.ts
├── components/pemali/     # SEMUA custom komponen
├── stores/                # Zustand stores
└── styles/globals.css     # CSS tokens PEMALI

---

## Dev environment

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Worker (terpisah)
python worker.py

# Frontend
cd frontend
pnpm install
pnpm dev
```

Env vars yang wajib ada (`.env`):
OPENROUTER_API_KEY=
DATABASE_URL=postgresql://...
CHROMA_HOST=localhost
CHROMA_PORT=8200
WORKER_POLL_INTERVAL=10

## Sprint Progress
- **Sprint 1 (Stabilisasi)**: ErrorResponse model, execute_with_safety(), scoped tool registry, DAG stress test. 20/20 test ✅
- **Sprint 2 (Cognitive Memory)**: TemporalPatternExtractor, KnowledgeGraphBuilder, MemoryNode/MemoryEdge tables, graph CRUD. 15/15 test ✅
- **Sprint 3 (Narrative + SDUI + Telemetry)**: IN PROGRESS — spec lengkap di `SPRINT_3_GUIDE.md`

---

## Coding style

- Python: type hints wajib di semua function signature. Black formatter.
  Docstring singkat (1 baris) untuk setiap public function.
- TypeScript: strict mode. No `any`. Zustand untuk state management.
- Commit format: `feat(scope): deskripsi` | `fix(scope): deskripsi`
- Minimal changes over full rewrites untuk backend.
- Full rewrites diperbolehkan untuk komponen frontend jika scope perubahan
  menyentuh >50% baris komponen.

---

## Anti-patterns (JANGAN LAKUKAN INI)

- Jangan taruh narasi/opini di dalam return value modul.
- Jangan import `worker.py` dari FastAPI app — mereka berjalan terpisah.
- Jangan hardcode agent name sebagai string di luar `agents/` directory.
- Jangan pakai Inter font, purple gradient on white, atau card default shadcn
  tanpa reskin ke PEMALI tokens.
- Jangan buat komponen baru di `components/ui/` — semua custom ke
  `components/pemali/`.
- Jangan langsung query ChromaDB — selalu lewat `core/memory.py` → `query_semantic()`.