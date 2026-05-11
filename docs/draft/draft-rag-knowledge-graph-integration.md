# Draft: Integrasi Knowledge Graph ke RAG Pipeline

## Frontend — Arah Desain Baru (Mei 2026)
User melakukan redesign total dashboard menjadi **light theme** (stone-900, bg-white, serif).
Gaya: editorial/minimal ala Claude — centered chat, sidebar history, tanpa tab system.
Tidak menggunakan PEMALI CSS tokens. Sprint 3 components (NarrativeCard, DAGViewer, NarrativeStream)
perlu di-adapt ke tema ini jika ingin di-integrasikan.

---

## Masalah
Knowledge graph (PostgreSQL `memory_nodes` + `memory_edges`) saat ini hanya diisi
setelah audit selesai via `insert_memory_graph()`, tapi TIDAK PERNAH di-query
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
1. Tambah `query_memory_graph_for_context()` di `core/memory.py` — query trending issues/locations
2. Di `PemaliOrchestrator.run()` — parallel query ChromaDB + PostgreSQL, gabung hasilnya
3. Format output graph sebagai tambahan konteks di system prompt

## Catatan
- Embedding model mismatch: AGENTS.md bilang `intfloat/multilingual-e5-base`, implementasi pakai `paraphrase-multilingual-MiniLM-L12-v2`
- `allow_reset=True` di ChromaDB riskan
- No deduplication di `insert_memory_graph()` — bisa duplicate nodes tiap session

---

# Draft: Module Development — Sprint 4

## Masalah
Saat ini hanya ada 2 module terdaftar: `mock_data_generator` dan `system_scheduler`.
Manager Agent mengirim task ke `geo_agent`, `water_agent`, `fire_agent`, `osint_agent`
tapi module dengan prefix `geo_*`, `satellite_*`, `water_*`, `fire_*`, `osint_*` TIDAK ADA.
Akibatnya:

1. Agent dapet **tools list kosong** (scope filter gak match apapun)
2. LLM dipanggil dengan `tools=[]` → bingung → nunggu response lama
3. 45 detik kemudian timeout → error
4. DAG mandek, cuma `scheduler_agent` yang bisa jalan (pake `mock_data_generator`)

## Target Arsitektur Module

```
modules/
├── geo_module.py        # Data geospasial & NDVI
│   → geo_sensor, satellite_imagery, mapping_ndvi
├── water_module.py      # Kualitas air & hidrologi
│   → water_quality, hydrology_flow, water_pH
├── fire_module.py       # Deteksi kebakaran & hotspot
│   → fire_hotspot, thermal_detection, burn_analysis
├── osint_module.py      # Intelijen berita & media
│   → osint_news, osint_scrape, osint_social
├── scheduler_mod.py     # (existing)
└── mock_module.py       # (existing, untuk testing)
```

## Spesifikasi Module (UTI V2)

### geo_module.py
```python
class GeoModule(PemaliModule):
    name = "geo_sensor"
    description = "Ambil data geospasial dan NDVI untuk suatu lokasi"
    parameters = {
        "location": {"type": "string", "description": "Nama lokasi di Bali"},
        "lat": {"type": "number", "description": "Latitude"},
        "lng": {"type": "number", "description": "Longitude"},
    }

    async def execute(self, params) -> PemaliOutput:
        # Mock: return dummy NDVI + koordinat
        return PemaliOutput(
            status="success",
            data={"ndvi": 0.32, "temperature": 31.5, "location": params["location"]},
            agent_hint="Data satelit menunjukkan...",
            thk_alignment={"palemahan": "..."}
        )
```

Semua module ikut pola yang sama — `PemaliModule` base class, Pydantic input,
return `PemaliOutput`. Untuk Sprint 4 cukup pake **mock data dulu** (sensor real
butuh API key Google Earth Engine, NASA FIRMS, dll).

## SCOPE_MAP update
```python
SCOPE_MAP = {
    "geo_agent": ["geo_*", "satellite_*", "mapping_*"],
    "water_agent": ["water_*", "hydrology_*"],
    "fire_agent": ["fire_*", "thermal_*"],
    "osint_agent": ["osint_*", "news_*", "scrape_*"],
}
```
Module yang dibuat harus sesuai pattern ini biar auto-match.

## File yang akan dibuat

| File | Deskripsi |
|------|-----------|
| `modules/geo_module.py` | Data geospasial: NDVI, suhu permukaan, koordinat |
| `modules/water_module.py` | Kualitas air: pH, debit, kekeruhan |
| `modules/fire_module.py` | Hotspot kebakaran: suhu, titik api, risiko |
| `modules/osint_module.py` | Intelijen: scraping berita lingkungan |

## Testing
- Test manual lewat TUI Chat: ketik "Audit Gianyar"
- Pastikan semua 4 agent baru bisa panggil module masing-masing
- Nggak ada lagi stuck di THK

## Prioritas
1. **Sprint 4a** — Buat 4 module dengan mock data (biar agent flow jalan)
2. **Sprint 4b** — Knowledge Graph RAG integration
3. **Sprint 4c** — Ganti mock data ke real API (Google Earth Engine, dll)
