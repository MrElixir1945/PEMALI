# PEMALI V2 — Architecture Draft & Roadmap

> **Status:** Sprint 1 & 2 — SELESAI | Sprint 3 — SEBAGIAN BESAR SELESAI | Sprint 4 — PLANNED  
> **Test:** 43/43 passing  
> **Branch:** `fitur/new-baseline`  
> **Terakhir Diupdate:** 2026-05-11  
> **Versi:** 0.3-beta

---

## 1. Ringkasan Visi

Platform audit lingkungan otonom berbasis AI yang **transparan**, **dapat belajar dari pengalaman**, dan **dapat dikembangkan komunitas** tanpa perlu mengubah core agent.

---

## 2. Struktur Proyek (Current)

```
pemali/
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── worker.py                  # Tick engine daemon
│   ├── requirements.txt           # Pinned dependencies
│   ├── core/
│   │   ├── base_module.py         # PemaliModuleV2 ABC
│   │   ├── database.py            # SQLAlchemy ORM models
│   │   ├── memory.py              # ChromaDB RAG + Graph CRUD
│   │   ├── memory_processor.py    # TemporalPatternExtractor + KG Builder
│   │   ├── models.py              # Pydantic schemas (TelemetryEvent, ErrorResponse, SDUIConfig)
│   │   ├── orchestrator.py        # PemaliOrchestrator + SubAgent (507 lines)
│   │   ├── registry.py            # Module auto-discovery
│   │   └── telemetry.py           # SSE event manager
│   ├── modules/
│   │   ├── mock_module.py         # MockDataGenerator (testing)
│   │   └── scheduler_mod.py       # SystemSchedulerModule
│   └── tests/
│       ├── test_dag_stress.py     # 20 tests — topology, scoped tools, error handling
│       ├── test_cognitive_memory.py # 15 tests — extractor, builder, graph CRUD
│       └── test_narrative.py      # 8 tests — TelemetryEvent, NarrativeContract, duration tracking
├── frontend/
│   └── src/
│       ├── app/                   # Next.js App Router pages
│       ├── components/pemali/     # NarrativeCard, NarrativeStream, DAGViewer
│       └── stores/               # Zustand telemetryStore
├── config/
│   ├── .env                       # (gitignored)
│   └── .env.example               # Template konfigurasi
├── docs/
│   ├── DRAFT_ARCHITECTURE.md      # Dokumen ini
│   ├── draft/                     # Draft spesifikasi upcoming
│   └── guides/                    # Development & module guides
├── infra/                         # Docker Compose, dev scripts
├── tools/                         # TUI chat & monitor
└── .gitignore
```

---

## 3. Progres Implementasi

### Sprint 1: Stabilisasi — ✅ SELESAI (20/20 test)

| # | Perbaikan | Selesai |
|---|-----------|---------|
| 1 | ErrorResponse model + execute_with_safety() + timeout 45s | ✅ |
| 2 | Scoped Tool Registry (get_scoped_manifests per domain) | ✅ |
| 3 | DAG Stress Test (5+ node dependen, deadlock, parallel) | ✅ |
| 4 | Shared Context Handler (_ERROR_ marker) | ✅ |
| 5 | Synthesis with Failures (partial report informatif) | ✅ |

### Sprint 2: Cognitive Memory Engine — ✅ SELESAI (15/15 test)

| # | Komponen | Selesai |
|---|----------|---------|
| 1 | TemporalPatternExtractor | ✅ |
| 2 | KnowledgeGraphBuilder | ✅ |
| 3 | memory_nodes + memory_edges tables | ✅ |
| 4 | Graph CRUD (insert, query, get_by_session) | ✅ |
| 5 | Orchestrator Integration (extract pattern post-audit) | ✅ |

### Sprint 3: Narrative + SDUI + Telemetry — 🔶 SEBAGIAN BESAR SELESAI

| # | Task | Status | File |
|---|------|--------|------|
| 1 | TelemetryEvent.metadata field | ✅ | `core/models.py` |
| 2 | .dict() → .model_dump() di telemetry | ✅ | `core/telemetry.py` |
| 3 | SubAgent NARRATIVE CONTRACT prompt | ✅ | `core/orchestrator.py:105-130` |
| 4 | Duration tracking (time.monotonic()) | ✅ | `core/orchestrator.py:258-278` |
| 5 | RAG context injection di Manager prompt | ✅ | `core/orchestrator.py:307-311` |
| 6 | Manager Agent NARRATIVE CONTRACT prompt | ❌ | Belum (desain sudah dibahas) |
| 7 | NarrativeStream.tsx (SSE consumer) | ✅ | `frontend/src/components/pemali/` |
| 8 | NarrativeCard.tsx (event card) | ✅ | `frontend/src/components/pemali/` |
| 9 | DAGViewer.tsx (SVG visualizer) | ✅ | `frontend/src/components/pemali/` |
| 10 | telemetryStore.ts (Zustand) | ✅ | `frontend/src/stores/` |
| 11 | test_narrative.py | ✅ | 8/8 pass |
| 12 | AgentCard.tsx | ❌ | Belum |
| 13 | TelemetryFeed.tsx | ❌ | Belum (digantikan NarrativeStream) |
| 14 | ModuleOutput.tsx (SDUI render) | ❌ | Belum |
| 15 | ChatInput.tsx | ❌ | Inline di dashboard |
| 16 | CSS tokens PEMALI di globals.css | ❌ | Belum (komponen pakai var(--pemali-*) tapi tidak didefinisikan) |
| 17 | Wire komponen ke dashboard page | ❌ | Belum |

**Test:** 43/43 passing (20 Sprint 1 + 15 Sprint 2 + 8 Sprint 3)

### Sprint 4: Module Development — ❌ BELUM DIMULAI

| # | Module | Status |
|---|--------|--------|
| 1 | geo_module.py (geo_sensor) | ❌ |
| 2 | water_module.py (water_quality) | ❌ |
| 3 | fire_module.py (fire_hotspot) | ❌ |
| 4 | osint_module.py (osint_news) | ❌ |

**Impact:** Tanpa module ini, `geo_agent`, `water_agent`, `fire_agent`, `osint_agent` dapat tools kosong → timeout 45s → error.

### Sprint 4b: Knowledge Graph RAG Integration — ❌ BELUM DIMULAI

`query_memory_graph()` ada di `core/memory.py` tapi tidak pernah dipanggil di production. Data PostgreSQL (`memory_nodes` + `memory_edges`) masuk tapi tidak dibaca.

---

## 4. Backend Fixes (2026-05-11)

| # | Fix | File |
|---|-----|------|
| 1 | Module path slash → dot notation | `core/registry.py:23` |
| 2 | Missing `__init__.py` di semua package | `backend/`, `core/`, `modules/`, `tests/` |
| 3 | load_dotenv() path absolute | `main.py:23`, `core/database.py:8` |
| 4 | Test patch paths (core. → backend.core.) | `tests/test_narrative.py:102,136` |
| 5 | Pydantic .json() → .model_dump_json() | `core/registry.py:57` |
| 6 | Naive datetime → UTC | `main.py:103` |
| 7 | init_db() di test cognitive memory | `tests/test_cognitive_memory.py` |
| 8 | SQLAlchemy declarative_base() deprecated | `core/database.py:4` |
| 9 | ChromaDB path absolute | `core/memory.py:9` |
| 10 | allow_reset=True → False | `core/memory.py:14` |
| 11 | Logging model load + collection ready | `core/memory.py:18,24` |
| 12 | Fix venv pip script path | `backend/.venv/bin/pip*` |
| 13 | requirements.txt moved + pinned + pytest | `backend/requirements.txt` |
| 14 | .gitignore robust | `.gitignore` → `**/venv/`, `**/.venv/`, `.opencode/`, `graphify-out/` |

---

## 5. Masalah Tertangani

| # | Masalah Sebelumnya | Fix | Status |
|---|-------------------|-----|--------|
| 1 | `raise he` crash orchestrator | ErrorResponse + execute_with_safety() | ✅ |
| 2 | Error return jadi `{}` di Manager | _ERROR_ marker di shared_context | ✅ |
| 3 | Sub-Agent bawa SEMUA tools | get_scoped_manifests() per domain | ✅ |
| 4 | Shared context rapuh | Error metadata + partial report | ✅ |
| 5 | RAG tidak belajar | TemporalPatternExtractor + KnowledgeGraphBuilder | ✅ |
| 6 | Module registry tidak load module | slash → dot notation | ✅ |
| 7 | load_dotenv gagal dari subdirectory | path absolute | ✅ |
| 8 | API key OpenRouter terekspos di repo | `**/.env` di .gitignore | ✅ |
| 9 | ChromaDB path inconsistent | path absolute | ✅ |
| 10 | allow_reset=True (dangerous) | allow_reset=False | ✅ |
| 11 | pip script broken di venv | fix shebang path | ✅ |

---

## 6. Masalah Known (Belum Diatasi)

| # | Masalah | Dampak | Sprint |
|---|---------|--------|--------|
| 1 | Manager prompt belum NARRATIVE CONTRACT | Manager tidak "bercerita" di SSE | Sprint 3 pending |
| 2 | 4 module (geo, water, fire, osint) tidak ada | Agent dapat tools kosong → timeout | Sprint 4 |
| 3 | query_memory_graph() tidak dipakai di production | Knowledge graph tidak untuk decision-making | Sprint 4b |
| 4 | No deduplication di insert_memory_graph() | Bisa duplicate nodes | Sprint 4b |
| 5 | CSS tokens PEMALI tidak didefinisikan | Komponen frontend render dengan fallback | Frontend |
| 6 | 4 komponen frontend belum ada | AgentCard, TelemetryFeed, ModuleOutput, ChatInput | Frontend |
| 7 | Embedding model mismatch | AGENTS.md vs implementasi (beda dimensi) | Migration |

---

## 7. Prioritas Ke Depan

1. **Sprint 3 sisa** — Manager Agent prompt (NARRATIVE CONTRACT + narasi)
2. **Sprint 4** — 4 module mock (geo, water, fire, osint) agar agent flow jalan
3. **Sprint 4b** — Knowledge Graph RAG (query_memory_graph ke prompt)
4. **Frontend** — CSS tokens, missing components, wire ke dashboard
5. **Sprint 4c** — Ganti mock data ke real API

---

## 8. Risiko & Mitigasi

| Risiko | Mitigasi | Prioritas |
|--------|---------|-----------|
| OpenRouter rate limit / downtime | Retry + exponential backoff | 🟡 Medium |
| Agent timeout karena tools kosong | Sprint 4 — module mock | 🔴 High |
| Knowledge graph data masuk tapi tidak dibaca | Sprint 4b — integrasi query | 🟡 Medium |
| Frontend CSS tokens missing | Sprint 3 sisa — define tokens | 🟡 Medium |
| Model embedding mismatch | Migration plan jika ganti model | 🟢 Low |

---

*Dokumen diperbarui: 2026-05-11. Branch: fitur/new-baseline.*
