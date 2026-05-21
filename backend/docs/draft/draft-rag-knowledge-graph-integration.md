# Draft: Integrasi Knowledge Graph ke RAG Pipeline

> **Status:** BELUM DIKERJAKAN — Sprint 4b  
> **Terakhir Diupdate:** 2026-05-11

---

## Masalah

Knowledge graph (PostgreSQL `memory_nodes` + `memory_edges`) saat ini hanya diisi
setelah audit selesai via `insert_memory_graph()`, tapi **TIDAK PERNAH** di-query
untuk decision-making. `query_memory_graph()` ada tapi tidak dipanggil di production code.

## Arsitektur Saat Ini

```
User Prompt → query_semantic() → ChromaDB (text report) → inject ke system prompt
                                                                         ↓
Cognitive Memory (post-execution): TemporalPatternExtractor → KnowledgeGraphBuilder → insert_memory_graph()
                                                                         ↓
                                                            Data masuk PostgreSQL, TIDAK PERNAH dibaca lagi
```

## Target Arsitektur

```
User Prompt
  ↓
query_semantic() → ChromaDB (text report)
  ↓
query_memory_graph() → PostgreSQL (knowledge graph: node relations, trends)
  ↓
Gabung kedua konteks → inject ke system prompt Manager Agent
  ↓
Eksekusi → Cognitive Memory → update graph lagi
```

## Data yang di-store di ChromaDB

- Document: string `"Audit Result: {synthesized LLM report}"`
- Metadata: `{session_id, timestamp}`
- Embedding: `paraphrase-multilingual-MiniLM-L12-v2` (384d)
- Collection: `pemali_audit_logs`
- Path: absolute → `{project_root}/chroma_db/`
- allow_reset: `False` ✅ (fixed 2026-05-11)

## Data yang di-store di PostgreSQL (Knowledge Graph)

### memory_nodes

| Field | Contoh |
|-------|--------|
| node_type | `"location"` / `"issue"` / `"metric"` |
| label | `"Ubud"` / `"deforestation"` / `"ndvi"` |
| properties | `{"name":"Ubud", "first_seen":"..."}` |
| session_id | `"tr-1234567890"` |

### memory_edges

| Field | Contoh |
|-------|--------|
| source_label | `"Ubud"` |
| target_label | `"deforestation"` |
| relation_type | `"has_issue"` / `"has_metric"` |
| weight | `85` |
| temporal_context | `{"season":"dry", "timestamp":"..."}` |

## Rencana Integrasi

1. Tambah `query_memory_graph_for_context()` di `backend/core/memory.py` — query trending issues/locations
2. Di `PemaliOrchestrator.run()` — parallel query ChromaDB + PostgreSQL, gabung hasilnya
3. Format output graph sebagai tambahan konteks di system prompt Manager Agent

## Catatan (Updated 2026-05-11)

- Embedding model: `paraphrase-multilingual-MiniLM-L12-v2` (384d). AGENTS.md menyebut `intfloat/multilingual-e5-base` (768d) — mismatch, perlu migration plan jika ganti model.
- `allow_reset=True` → **sudah difix** ke `False` (2026-05-11)
- ChromaDB path → **sudah difix** ke absolute (2026-05-11)
- Model log → **sudah ditambah** logging saat load model + collection ready (2026-05-11)
- No deduplication di `insert_memory_graph()` — **belum difix**, bisa duplicate nodes tiap session.

---

# Draft: Module Development — Sprint 4

> **Status:** BELUM DIKERJAKAN  
> **Prioritas:** HIGH — agent flow stuck tanpa module

## Masalah

Saat ini hanya ada 2 module terdaftar: `mock_data_generator` dan `system_scheduler`.
Manager Agent mengirim task ke `geo_agent`, `water_agent`, `fire_agent`, `osint_agent`
tapi module dengan prefix `geo_*`, `satellite_*`, `water_*`, `fire_*`, `osint_*` **TIDAK ADA**.

Akibatnya:

1. Agent dapet **tools list kosong** (scope filter gak match apapun)
2. LLM dipanggil dengan `tools=[]` → bingung → nunggu response lama
3. 45 detik kemudian timeout → error
4. DAG mandek, cuma `scheduler_agent` yang bisa jalan (pake `mock_data_generator`)

## Target Arsitektur Module

```
backend/modules/
├── geo_module.py         # geo_sensor — Data geospasial & NDVI
├── water_module.py       # water_quality — Kualitas air & hidrologi
├── fire_module.py        # fire_hotspot — Deteksi kebakaran & hotspot
├── osint_module.py       # osint_news — Intelijen berita & media
├── scheduler_mod.py      # system_scheduler (existing)
└── mock_module.py        # mock_data_generator (existing, testing)
```

## SCOPE_MAP (sudah ada di orchestrator.py)

```python
SCOPE_MAP = {
    "geo_agent": ["geo_*", "satellite_*", "mapping_*"],
    "water_agent": ["water_*", "hydrology_*"],
    "fire_agent": ["fire_*", "thermal_*"],
    "osint_agent": ["osint_*", "news_*", "scrape_*"],
}
```

Module dibuat dengan pattern UTI V2 (PemaliModuleV2, Pydantic input_schema, async execute, ModuleOutput).

## File yang akan dibuat

| File | Module Name | Deskripsi |
|------|-------------|-----------|
| `modules/geo_module.py` | `geo_sensor` | Data geospasial: NDVI, suhu permukaan, koordinat |
| `modules/water_module.py` | `water_quality` | Kualitas air: pH, debit, kekeruhan |
| `modules/fire_module.py` | `fire_hotspot` | Hotspot kebakaran: suhu, titik api, risiko |
| `modules/osint_module.py` | `osint_news` | Intelijen: scraping berita lingkungan |

## Prioritas

1. **Sprint 4a** — Buat 4 module dengan mock data (biar agent flow jalan)
2. **Sprint 4b** — Knowledge Graph RAG integration (query_memory_graph ke prompt)
3. **Sprint 4c** — Ganti mock data ke real API (Google Earth Engine, NASA FIRMS, dll)
