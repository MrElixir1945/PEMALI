# PEMALI V2 Architecture Draft & Roadmap

> **Status:** Sprint 1 & 2 — SELESAI (35/35 test passing)  
> **Terakhir Diupdate:** 2025-05-09  
> **Versi:** 0.2-beta  

---

## 1. Ringkasan Visi

Platform audit lingkungan otonom berbasis AI yang **transparan**, **dapat belajar dari pengalaman**, dan **dapat dikembangkan komunitas** tanpa perlu mengubah core agent.

---

## 2. Progres Implementasi

### Sprint 1: Stabilisasi — ✅ SELESAI (20/20 test)

| # | Perbaikan | Status | File | Test |
|---|-----------|--------|------|------|
| 1 | **Error Handling Robust** — `ErrorResponse` model, `execute_with_safety()`, timeout 45s | ✅ Done | `core/models.py`, `core/orchestrator.py` | `test_dag_stress.py` |
| 2 | **Scoped Tool Registry** — Sub-Agent hanya lihat tools domain-nya | ✅ Done | `core/orchestrator.py` | `test_dag_stress.py` |
| 3 | **DAG Stress Test** — 5+ node dependen, deadlock detection, parallel siblings | ✅ Done | `tests/test_dag_stress.py` | 20 test |
| 4 | **Shared Context Handler** — Error task disimpan sebagai `_ERROR_` marker | ✅ Done | `core/orchestrator.py` | `test_dag_stress.py` |
| 5 | **Synthesis with Failures** — Partial report tetap informatif | ✅ Done | `core/orchestrator.py` | `test_dag_stress.py` |

### Sprint 2: Cognitive Memory Engine — ✅ SELESAI (15/15 test)

| # | Komponen | Status | File | Test |
|---|----------|--------|------|------|
| 1 | **TemporalPatternExtractor** — Ekstrak pola temporal dari hasil audit | ✅ Done | `core/memory_processor.py` | `test_cognitive_memory.py` |
| 2 | **KnowledgeGraphBuilder** — Bangun node & edge relasi | ✅ Done | `core/memory_processor.py` | `test_cognitive_memory.py` |
| 3 | **Knowledge Graph Tables** — `memory_nodes` + `memory_edges` di PostgreSQL | ✅ Done | `core/database.py` | `test_cognitive_memory.py` |
| 4 | **Graph CRUD** — `insert_memory_graph()`, `query_memory_graph()` | ✅ Done | `core/memory.py` | `test_cognitive_memory.py` |
| 5 | **Orchestrator Integration** — Ekstrak pattern setelah audit selesai | ✅ Done | `core/orchestrator.py` | Manual test |

**Total:** 35/35 test passing ✅

---

## 3. Temuan & Arsitektur Tertangani

### 3.1 Masalah Critical — SUDAH DIPERBAIKI

| # | Masalah Sebelumnya | Fix Yang Diimplementasi | Status |
|---|-------------------|-----------------------|--------|
| 1 | `raise he` crash orchestrator | `ErrorResponse` terstruktur + `execute_with_safety()` | ✅ Fixed |
| 2 | Error return jadi `{}` di Manager | `_ERROR_` marker di `shared_context` | ✅ Fixed |
| 3 | Sub-Agent bawa SEMUA tools | `get_scoped_manifests()` per domain | ✅ Fixed |
| 4 | Shared context rapuh | Error metadata + partial report | ✅ Fixed |
| 5 | RAG tidak belajar | `TemporalPatternExtractor` + `KnowledgeGraphBuilder` | ✅ Fixed |

---

## 4. Rancangan Sprint 3: SDUI + Telemetry Narrative (Fase 4 Awal)

### 4.1 Sistem Narasi Transparan (Prompt Contracts)

**Manager Agent Prompt (`system_prompt`) di `core/orchestrator.py`:**

```
[PEMALI NARRATIVE CONTRACT v1]

Anda adalah MANAGER AGENT. Tugas: analisis, delegasi, sintesis.

SEBELUM setiap aksi:
  EMIT TelemetryEvent dengan narrative bahasa manusia.
  Ceritakan: apa yang Anda pikirkan, kenapa memutuskan demikian.

FORMAT NARRATIVE (untuk user):
"🧠 Manager Agent sedang berpikir: Berdasarkan memori audit sebelumnya 
di Gianyar... Saya mendeteksi pola deforestasi di musim kemarau. 
Saya akan prioritaskan pengumpulan data NDVI."

FORMAT TEKNIS (output JSON tetap sama):
{'trace_id': '...', 'tasks': [...]}
```

**Sub-Agent Prompt (`system_prompt`):**

```
[PEMALI NARRATIVE CONTRACT v1]

Anda adalah {target_agent}. Tugas: {intent}.

SEBELUM memilih tools:
  EMIT: "Saya sedang mempertimbangkan tools mana yang paling sesuai..."

SEBELUM eksekusi tools:
  EMIT: "Saya menggunakan [tool_name] untuk [tujuan]..."

SAAT error:
  EMIT: "Terjadi masalah saat [tool_name]: [ringkasan error]. 
         Saya akan mencoba koreksi dengan [strategi]."

FORMAT TEKNIS: function-calling JSON standard
```

### 4.2 Server-Driven UI (SDUI)

**Backend: `ModuleOutput` dengan `SDUIConfig`**

```python
class ModuleOutput(BaseModel):
    status: int
    data: Dict[str, Any]
    error_msg: Optional[str] = None
    sdui_config: Optional[SDUIConfig] = None  # ← TAMBAH INI

class SDUIConfig(BaseModel):
    ui_type: str        # 'metric_card', 'map_layer', 'data_table', 'timeline_plot'
    position: str       # 'full_width', 'half_width', 'sidebar'
    theme: str          # 'default', 'alert_red', 'warning_amber', 'success_green'
    refresh_rate_ms: int = 5000
```

**Frontend: Component Mapping**

| `ui_type` | React Component | Library |
|-----------|----------------|---------|
| `metric_card` | `<MetricCard />` | Tailwind + Framer Motion |
| `map_layer` | `<LeafletMapLayer />` | react-leaflet |
| `data_table` | `<DataTable />` | TanStack Table |
| `timeline_plot` | `<RechartsTimeline />` | Recharts |
| `telemetry_chart` | `<RealTimeChart />` | Recharts + SSE |

### 4.3 Frontend Component: NarrativeStream

```tsx
// frontend/src/components/NarrativeStream.tsx
interface TelemetryEvent {
  trace_id: string;
  node_id: string;
  node_type: 'Manager' | 'SubAgent' | 'Module';
  state: 'THINKING' | 'SPAWNING' | 'EXECUTING' | 'ERROR' | 'DONE';
  narrative: string;        // Narasi bahasa manusia
  timestamp: number;
  metadata?: {
    tools_used?: string[];
    sub_agents_spawned?: string[];
    rag_sources?: string[];
  }
}
```

**SSE Wiring:**
```typescript
const eventSource = new EventSource('/api/telemetry?trace_id=' + traceId);
eventSource.onmessage = (e) => {
  const data: TelemetryEvent = JSON.parse(e.data);
  setEvents(prev => [...prev, data]);
};
```

---

## 5. Rencana Implementasi Sprint 3 (1-2 minggu)

| Hari | Tugas | File | Estimasi |
|------|-------|------|----------|
| 1 | Implement narrative prompt contracts di Manager/Sub-Agent | `core/orchestrator.py` | 4h |
| 1 | Tambah `TelemetryEvent.metadata` field untuk tracking tools | `core/models.py` | 1h |
| 2 | Implement `NarrativeStream.tsx` component + styling | `frontend/src/components/` | 6h |
| 2 | Create `NarrativeCard.tsx` sub-component (yellow/blue cards) | `frontend/src/components/` | 3h |
| 3 | Wire SSE `/api/telemetry` ke frontend | `frontend/src/app/dashboard/page.tsx` | 4h |
| 3 | Add reconnection logic + buffer management (200 events) | `frontend/src/components/` | 3h |
| 4 | Write `MODULE_V2_GUIDE.md` dengan SDUI example | `docs/MODULE_V2_GUIDE.md` | 4h |
| 4 | Update `MODULE_TEMPLATE.md` dengan SDUI config | `MODULE_TEMPLATE.md` | 2h |
| 5 | Integration test: Full flow dari prompt → finish dengan SSE | `tests/` | 6h |

---

## 6. Risiko & Mitigasi

| Risiko | Mitigasi | Prioritas |
|--------|---------|-----------|
| OpenRouter rate limit / downtime | Fallback queue + exponential backoff (sudah basic retry) | 🟡 Medium |
| ChromaDB corruption | Backup collection sebelum operasi besar | 🟡 Medium |
| Telemetry text overflow (frontend) | Virtual scrolling + max 200 events + debounce | 🔴 High |
| Komunitas bingung dengan V2 standard | `MODULE_V2_GUIDE.md` + example repo | 🔴 High |

---

## 7. File yang Sudah Dibuat/Diubah

| File | Status | Tujuan |
|------|--------|--------|
| `core/models.py` | ✅ Modified | `ErrorResponse`, `TelemetryEvent` |
| `core/orchestrator.py` | ✅ Modified | Error handling, scoped tools, cognitive memory |
| `core/database.py` | ✅ Modified | `MemoryNode`, `MemoryEdge` tables |
| `core/memory.py` | ✅ Modified | Graph CRUD: `insert_memory_graph()`, `query_memory_graph()` |
| `core/memory_processor.py` | ✅ **NEW** | `TemporalPatternExtractor`, `KnowledgeGraphBuilder` |
| `tests/test_dag_stress.py` | ✅ **NEW** | 20 tests: topology, scoped tools, error handling |
| `tests/test_cognitive_memory.py` | ✅ **NEW** | 15 tests: extractor, builder, graph CRUD |
| `DRAFT_ARCHITECTURE.md` | ✅ Updated | Dokumentasi roadmap |

---

## 8. Catatan Diskusi Penting

### RAG vs Cognitive Memory
> RAG saat ini "sampah" — AI hanya text matching, tidak belajar.

**Status:** ✅ **TERATASI**
- `TemporalPatternExtractor` → ekstrak pola temporal (seasonality, anomaly, tren)
- `KnowledgeGraphBuilder` → bangun node/edge relasi entity
- AI kini melihat **pola** bukan hanya teks mentah

### Scoped Tools vs Global Tools
> Sub-Agent bawa semua tools = token waste & security risk.

**Status:** ✅ **TERATASI**
- `get_scoped_manifests()` → filter per domain (geo, water, fire, osint)
- Agent hanya lihat tools yang relevan

---

## 9. Action Items Checklist — Sprint 3

- [ ] **Implement narrative prompt contracts** (Day 1)
- [ ] **Add metadata field ke TelemetryEvent** (Day 1)
- [ ] **Build NarrativeStream.tsx + NarrativeCard.tsx** (Day 2)
- [ ] **Wire SSE telemetry ke frontend** (Day 3)
- [ ] **Add virtual scrolling + buffer management** (Day 3)
- [ ] **Write MODULE_V2_GUIDE.md** (Day 4)
- [ ] **Integration test: Full flow with SSE** (Day 5)

---

*Dokumen ini akan terus diperbarui sesuai progress Sprint 3.*