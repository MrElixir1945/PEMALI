# PEMALI V2 — AGENTS.md
# Programmable Entity for Multi-Agent Logical Inference

## Project overview

---

## Agent Working Contract

> Baca section ini sebelum nulis APAPUN — response, kode, atau penjelasan.
> Tujuan: hemat token, kualitas tetap tinggi, bahasa enak dibaca.
>
> Empiris: AGENTS.md yang well-formed terbukti kurangi runtime agent −28.64%
> dan output token −16.58% tanpa degradasi task completion
> (Lulla et al., 2026 — arXiv:2601.20404).

---

### A. Response Mode

Pilih mode sebelum mulai respond:

| Mode      | Kapan pakai                                              | Format output                          |
|-----------|----------------------------------------------------------|----------------------------------------|
| `BRIEF`   | Task < 20 baris, 1 file, perubahan jelas                 | Kode langsung + 1–2 baris konteks      |
| `NORMAL`  | Multi-file, perlu sedikit reasoning                      | Kode + penjelasan ringkas per bagian   |
| `VERBOSE` | Debug mode, user explicit minta explain, atau ada error  | Full reasoning + kode + trace          |

**Default: `BRIEF`.** Jangan escalate ke VERBOSE kecuali diperlukan atau diminta.

---

### B. Code-First, Explain-After

Urutan wajib:
1. Tulis kode dulu — lengkap, bisa langsung dipakai
2. Baru penjelasan singkat di bawah (maks 3–5 baris untuk BRIEF/NORMAL)

❌ Jangan:
```
"Oke jadi gue akan buat fungsi yang melakukan X karena Y, 
dan pertimbangannya adalah Z... baru kemudian kodenya:"
```

✅ Lakukan:
```python
def do_x(param: str) -> dict:
    """Single-line docstring."""
    ...
```
> Penjelasan singkat di sini kalau perlu. Bukan sebelum kode.

---

### C. Diff Over Rewrite

- Perubahan **< 40% baris file** → kirim patch/diff saja, bukan full file
- Perubahan **≥ 40%** atau menyentuh struktur utama → full rewrite diperbolehkan
- Selalu sebut baris/fungsi mana yang berubah kalau kirim diff

Format diff yang disarankan (unified):
```diff
- old_line
+ new_line
```
Atau tunjuk langsung: *"ganti baris 42–55 di `agents/base_agent.py` dengan ini:"*

---

### D. Bahasa Mixing Rule

PEMALI adalah proyek bilingual by design. Aturannya:

| Konteks                        | Bahasa                        |
|-------------------------------|-------------------------------|
| Narasi, komentar inline       | Indonesia — santai tapi presisi |
| Nama var / func / class       | English, conventional          |
| Error message & log           | English (ecosystem standard)   |
| Docstring (public function)   | English singkat (1 baris)      |
| AGENTS.md & dokumentasi       | Indonesia boleh campur teknis  |

❌ Jangan campur di tengah kalimat:
```
# Fungsi ini will return null kalau data is empty
```

✅ Konsisten:
```python
# Kembalikan None kalau data kosong
def get_data(key: str) -> dict | None:
    """Return data by key, or None if not found."""
    ...
```

---

### E. Scope Confirmation

Sebelum mulai task yang besar, estimate dulu:

```
Estimasi:
- File yang disentuh : X file
- Baris perubahan   : ~Y baris
- Dependensi baru   : ada/tidak
```

**Wajib konfirmasi ke user jika:**
- Menyentuh > 5 file sekaligus
- Estimasi > 200 baris perubahan
- Ada perubahan breaking ke schema Pydantic atau API route

Jangan langsung eksekusi task besar tanpa alignment scope dulu.

---

### F. No Filler

Hapus semua kata-kata ini dari response:

❌ `"Great question!"` `"Sure!"` `"Certainly!"` `"Of course!"` `"Absolutely!"`  
❌ `"That's a good point."` `"Let me help you with that."`  
❌ Paragraf pembuka yang hanya repeat pertanyaan user

✅ Langsung jawab. Langsung kode. Langsung ke inti.

---

### G. Token Saver — Teknik Aktif

Teknik ini wajib dipakai secara sadar, bukan opsional:

#### G1. Lazy Context Loading
Jangan load atau sebut context yang tidak relevan dengan task saat ini.
Kalau task adalah "fix bug di `auditor_agent.py`" → jangan bahas `scheduler_agent` 
atau bagian frontend kecuali ada dependensi langsung.

#### G2. Reference Over Repeat
Kalau sudah ada fungsi/schema yang relevan di codebase:
- ❌ Copy-paste ulang kodenya di response
- ✅ Refer saja: *"gunakan `execute_with_safety()` yang sudah ada di `base_agent.py` baris 47"*

#### G3. Schema First, Impl Later
Untuk task baru yang kompleks:
1. Tulis schema/interface dulu (Pydantic model atau TypeScript type)
2. Tunggu konfirmasi
3. Baru implement

Ini cegah full rewrite kalau ternyata arah salah.

#### G4. Incremental Commit Pattern
Pecah task besar jadi commit kecil yang atomic. Tiap commit:
- Satu tujuan jelas
- Bisa di-review sendiri
- Tidak break hal lain

Format: `feat(auditor): tambah retry untuk tool call 5xx`  
Bukan: `feat: update banyak hal di agent dan frontend`

#### G5. Tiered Skill Loading (dari SkillReducer research)
Untuk task yang butuh skill/context tambahan:
- **Tier 1 (always)**: rules umum AGENTS.md ini
- **Tier 2 (on-demand)**: skill spesifik hanya dimuat kalau task butuh  
  contoh: `frontend-design` skill hanya dimuat kalau ada UI work
- **Tier 3 (explicit)**: dokumentasi detail, dimuat hanya kalau user minta

Jangan front-load semua context sekaligus di awal — muat bertahap.

#### G6. Compress Before Repeat
Kalau perlu menyebut ulang sesuatu yang sudah dibahas:
- ❌ Repeat verbatim
- ✅ 1 kalimat summary + referensi ke section/file aslinya

---

### Quick Reference Card

```
Task masuk
  ↓
Pilih mode: BRIEF / NORMAL / VERBOSE
  ↓
Estimate scope → konfirmasi kalau besar
  ↓
Lazy load context (G1) — hanya yang relevan
  ↓
Schema first kalau task baru (G3)
  ↓
Tulis kode → penjelasan singkat setelahnya (B)
  ↓
Diff kalau < 40% (C)
  ↓
Cek bahasa (D) → no filler (F)
  ↓
Done
```

---

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

---

## Frontend Engineering Standards

### Skills
Load these skills automatically based on task context:
- **frontend-design** — any UI component, page, or visual work
- **web-design-guidelines** — before finalizing any UI (accessibility + UX audit)
- **vercel-react-best-practices** — any React/Next.js code
- **vercel-composition-patterns** — reusable components or API design

---

### Anti-Slop Mandate

Before writing ANY frontend code, do this first:
1. List your 3 first instincts (font, color, layout)
2. REJECT all 3
3. Then choose something intentional

#### Forbidden
- ❌ Inter, Roboto, Arial, Space Grotesk as display font
- ❌ Purple/blue gradient on white background
- ❌ Centered H1 + subtitle + 2 CTA buttons hero
- ❌ Generic rounded card: icon + title + body + shadow
- ❌ Hardcoded `animationDelay` per element — use `staggerChildren`
- ❌ Glassmorphism without a meaningful background behind it
- ❌ Equal padding on all sides as default layout

---

### Design Process

1. **Context** — Who uses this? What is the emotional goal?
2. **Direction** — Commit to ONE aesthetic, name it in a comment:
   `/* Direction: Refined Monochrome Editorial */`
3. **Unforgettable moment** — What is the ONE thing someone remembers?
4. **Motion plan** — Map entrance → interaction → exit before writing code

---

### Anthropic Design Language

When in doubt, lean toward Anthropic's aesthetic:
- **Tone**: Calm, confident, intelligent — never loud or gimmicky
- **Typography**: Serif or humanist sans with strong hierarchy — warm and considered
- **Color**: Restrained palette, cream/off-white backgrounds, deep neutrals, intentional accent
- **Spacing**: Generous whitespace, breathing room — content-first
- **Motion**: Subtle, purposeful, never decorative — entrances that feel like settling, not bouncing
- **Texture**: Soft grain overlays, gentle gradients — depth without noise
- **Components**: Clean edges, minimal borders, elevation through spacing not shadows
## Anthropic Design Language — Specifics

### Typography
- Display: ALWAYS use a warm serif — `Canela`, `Tiempos`, `Freight Display`, atau `Lora` 
  sebagai fallback. BUKAN geometric sans.
- Body: `Söhne`, `GT America`, atau `Source Serif 4` untuk readability
- Weight: restrained — tidak ada ultra-bold display. Max font-weight 500 untuk body, 
  600 untuk display heading

### Color — Anthropic Palette
- Background: `#F5F4EF` (warm parchment) — BUKAN cool gray atau pure white
- Text primary: `#1A1916` (warm near-black)
- Text muted: `#7A7670`
- Accent: `#C8A882` (warm sand/ochre) atau `#D4956A` (terracotta) — 
  BUKAN merah, BUKAN biru, BUKAN salmon yang terlalu vibrant
- Border: `rgba(26, 25, 22, 0.08)` — sangat subtle

### Tone & Atmosphere
- TIDAK ada terminal/code block di hero section — Anthropic communicate dengan prose
- TIDAK ada "hacker dashboard" aesthetic (status bars, live indicators yang flashy)
- Atmosphere: soft grain overlay (`opacity: 0.03–0.05`), gentle vignette — BUKAN flat
- Cards: subtle background differentiation (`#EFEDE6`) — BUKAN border yang strong

### Motion — Anthropic Feel
- Entrances: slow fade + slight upward drift — `duration: 0.7s, ease: [0.0, 0.0, 0.2, 1]`
- TIDAK ada spring yang elastic atau bounce
- TIDAK ada animasi yang "show off" — motion harus invisible, hanya terasa natural
- Hover states: opacity shift (`0.7 → 1`) atau subtle translate (`y: -2px`) — minimal

### Layout Pattern — Anthropic
- Left-aligned content, asymmetric dengan large empty right — BUKAN centered hero
- Numbering system: `01 ——— LABEL` pakai em-dash, bukan slash atau bullet
- Section separators: single `1px` hairline, warm tone
- CTA button: filled dark (`#1A1916`) dengan white text, rounded `6px` — simpel

---

### Animation Rules
Micro-interactions    →  CSS custom properties + keyframes
Component reveals     →  Framer Motion (staggerChildren + useInView)
Scroll storytelling   →  GSAP + ScrollTrigger
Page transitions      →  Framer Motion AnimatePresence

#### Framer Motion Patterns

```tsx
// ✅ Orchestrated stagger — always prefer this
const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.07, delayChildren: 0.1 }
  }
}
const item = {
  hidden: { opacity: 0, y: 16, filter: 'blur(4px)' },
  show: {
    opacity: 1, y: 0, filter: 'blur(0px)',
    transition: { duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }
  }
}

// ✅ Scroll-triggered
const { ref, inView } = useInView({ threshold: 0.15, triggerOnce: true })
<motion.div ref={ref} variants={container} animate={inView ? 'show' : 'hidden'} />

// ✅ Page transitions
<AnimatePresence mode="wait">
  <motion.div key={route} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
</AnimatePresence>

// ❌ Never hardcode delay per element
<motion.div transition={{ delay: 0.1 }} />
<motion.div transition={{ delay: 0.2 }} />
<motion.div transition={{ delay: 0.3 }} />
```

#### Easing — Anthropic Feel
```ts
// Preferred easings — feels considered, not bouncy
const ease = {
  out: [0.0, 0.0, 0.2, 1],       // smooth deceleration
  inOut: [0.4, 0.0, 0.2, 1],     // balanced
  spring: { type: 'spring', stiffness: 80, damping: 20 } // settled, not elastic
}

// Durations
// micro: 150ms | reveal: 400-600ms | page: 300ms
// NEVER exceed 700ms for UI transitions
```

#### Performance
- ONLY animate: `transform`, `opacity`, `filter`
- NEVER animate: `height`, `width`, `margin`, `padding`, `top`, `left`
- Always include reduced motion:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

### Typography

- Display: characterful, warm — serif or distinctive humanist sans
- Body: readable, refined — good x-height, comfortable tracking
- Import via `next/font` or `@fontsource` — never CDN in `<head>`
- Scale: use a modular type scale (1.25 or 1.333 ratio)
- Line height: 1.5–1.7 for body, 1.1–1.2 for display

### Color

- All colors via CSS custom properties — no hardcoded hex in JSX/TSX
- Base: off-white or warm cream (`#FAFAF8` range) — not pure white
- Text: near-black with warmth (`#1A1917` range) — not `#000000`
- Accent: one intentional color, used sparingly
- Dark mode: deep warm dark (`#141410` range), not `#000` or `#1a1a1a`

### Layout & Spacing

- Grid-breaking is intentional: asymmetry, overlap, diagonal flow
- Generous negative space — let content breathe
- Atmosphere: soft gradient mesh, grain texture, or layered transparency
- Background: NEVER default to flat `#fff` or `#000`

---

### CSS Architecture

```css
:root {
  /* Spacing */
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 2rem;
  --space-xl: 4rem;
  --space-2xl: 8rem;

  /* Typography */
  --font-display: 'YourDisplayFont', serif;
  --font-body: 'YourBodyFont', sans-serif;
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.25rem;
  --text-xl: 1.563rem;
  --text-2xl: 1.953rem;
  --text-3xl: 2.441rem;

  /* Colors */
  --color-bg: #FAFAF8;
  --color-bg-subtle: #F2F1EE;
  --color-text: #1A1917;
  --color-text-muted: #6B6860;
  --color-accent: /* one intentional color */;
  --color-border: rgba(26, 25, 23, 0.1);
}
```

---

### Pre-Submit Checklist

- [ ] Skill `frontend-design` loaded?
- [ ] Skill `web-design-guidelines` audited?
- [ ] Anti-slop: 3 instincts listed and rejected?
- [ ] Aesthetic direction named in comment?
- [ ] Hardcoded hex in JSX? → move to CSS vars
- [ ] Hardcoded `animationDelay`? → refactor to `staggerChildren`
- [ ] Animating layout properties? → switch to `transform`/`opacity`
- [ ] Generic display font? → replace
- [ ] Flat white/black background? → add atmosphere
- [ ] Would a senior Anthropic designer be proud of this?