# 🌿 PEMALI — Development Documentation
> Platform Ekologi Modular Agentic berbasis Artificial Intelligence  
> Versi: 0.1.0-prototype | Timeline: 13 Hari | Tim: 2 Developer

---

## 📁 Struktur Repositori

```
pemali/
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── agents/
│   │   ├── orchestrator.py        # Agen Orkestrator utama
│   │   ├── satellite_agent.py     # Modul 1 — Satellite Monitor
│   │   ├── osint_agent.py         # Modul 2 — OSINT Social Listener
│   │   ├── scoring_agent.py       # Modul 3 — Priority Scoring Engine
│   │   └── policy_agent.py        # Modul 4 — Local Policy Analyzer
│   ├── models/
│   │   ├── schemas.py             # Pydantic models
│   │   └── database.py            # SQLite/PostgreSQL setup
│   ├── services/
│   │   ├── gee_service.py         # Google Earth Engine integration
│   │   ├── twitter_service.py     # Tweepy integration
│   │   ├── youtube_service.py     # YouTube Data API v3
│   │   └── nlp_service.py         # IndoBERT sentiment analysis
│   └── requirements.txt
├── frontend/
│   ├── pages/
│   │   ├── index.tsx              # Dashboard utama
│   │   └── report/[id].tsx        # Halaman laporan desa
│   ├── components/
│   │   ├── MapHeatmap.tsx         # Visualisasi NDVI heatmap
│   │   ├── ScoreCard.tsx          # Priority score card
│   │   └── AuditReport.tsx        # Laporan audit THK
│   └── tailwind.config.ts
├── data/
│   ├── regions.json               # Koordinat wilayah pilot
│   └── thk_parameters.json        # Parameter Tri Hita Karana
├── .env.example
└── README.md
```

---

## ⚙️ Tech Stack

| Komponen | Teknologi | Versi | Keterangan |
|---|---|---|---|
| **Backend** | Python + FastAPI | 3.11 / 0.110+ | API layer utama |
| **Agent Framework** | LangChain atau CrewAI | latest | Backbone orkestrator — putuskan Hari 1 |
| **Satellite Data** | Google Earth Engine Python API | latest | Free tier, butuh registrasi |
| **OSINT Twitter/X** | Tweepy | 4.x | Rate limit harus dimanage |
| **OSINT YouTube** | YouTube Data API v3 | v3 | Via Google Cloud Console |
| **OSINT Facebook** | CrowdTangle | — | Research access — apply dulu |
| **NLP/Sentiment** | HuggingFace + IndoBERT | indobenchmark/indobert-base-p1 | Custom vocab bahasa Bali |
| **Database** | SQLite (proto) → PostgreSQL | — | SQLite cukup untuk 13 hari |
| **Frontend** | Next.js + Tailwind CSS | 14+ / 3.x | Dashboard peta + skor |
| **Deployment** | Railway/Render + Vercel | — | Backend + Frontend terpisah |

---

## 🔧 Setup & Instalasi

### Prerequisites
```bash
python >= 3.11
node >= 18.x
git
```

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env dengan API keys masing-masing
```

### Environment Variables (`.env`)
```env
# Google Earth Engine
GEE_PROJECT_ID=your-gee-project-id
GEE_SERVICE_ACCOUNT=your-service-account@project.iam.gserviceaccount.com
GEE_KEY_FILE=path/to/gee-key.json

# Twitter/X (Tweepy)
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_BEARER_TOKEN=

# YouTube Data API v3
YOUTUBE_API_KEY=

# Facebook CrowdTangle
CROWDTANGLE_API_TOKEN=

# HuggingFace
HF_MODEL_NAME=indobenchmark/indobert-base-p1

# Database
DATABASE_URL=sqlite:///./pemali.db
# DATABASE_URL=postgresql://user:pass@localhost/pemali

# LangChain / OpenAI (jika pakai LLM)
OPENAI_API_KEY=
LANGCHAIN_TRACING_V2=false
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🏗️ Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────┐
│                    PEMALI SYSTEM                        │
│                                                         │
│  INPUT                OTAK               OUTPUT         │
│  ┌────────┐    ┌──────────────────┐    ┌────────────┐  │
│  │Satelit │───▶│                  │    │  Laporan   │  │
│  │(NDVI)  │    │  Agen            │───▶│  ke Desa   │  │
│  └────────┘    │  Orkestrator     │    │  Adat      │  │
│  ┌────────┐    │                  │    └────────────┘  │
│  │ OSINT  │───▶│  (LangChain /    │                    │
│  │ Sosmed │    │   CrewAI)        │    ┌────────────┐  │
│  └────────┘    └──────┬───────────┘    │ Dashboard  │  │
│                       │               │  Next.js   │  │
│              ┌────────▼────────┐      └────────────┘  │
│              │ Priority Score  │                       │
│              │ + THK Filter    │                       │
│              └─────────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

### Dua Opsi Arsitektur Agent

| | Opsi A: LangChain/CrewAI | Opsi B: Custom Orkestrator |
|---|---|---|
| **Keunggulan** | Cepat, dokumentasi lengkap | Full control arsitektur |
| **Keunggulan** | Cocok untuk 13 hari | Lebih defensible saat pitch |
| **Kelemahan** | Terikat opinionated architecture | Butuh waktu lebih |
| **Kelemahan** | Kurang "milik sendiri" | 13 hari sangat mepet |
| **Rekomendasi** | ✅ Untuk prototype lomba | Untuk produk jangka panjang |

---

## 🛰️ Modul 1 — Satellite Environmental Monitor

**Tujuan:** Mendeteksi perubahan tutupan lahan hijau via citra satelit (NDVI).

**Wilayah Pilot:** Bedugul, Ubud, Buleleng

### Pseudocode
```python
# backend/agents/satellite_agent.py
import ee
from datetime import datetime, timedelta

class SatelliteAgent:
    def __init__(self):
        ee.Initialize(project=GEE_PROJECT_ID)
        self.pilot_regions = {
            "bedugul": ee.Geometry.Rectangle([115.15, -8.30, 115.25, -8.20]),
            "ubud":    ee.Geometry.Rectangle([115.25, -8.52, 115.35, -8.42]),
            "buleleng": ee.Geometry.Rectangle([115.05, -8.15, 115.15, -8.05]),
        }

    def get_ndvi(self, region_name: str, months_back: int = 6) -> dict:
        region = self.pilot_regions[region_name]
        end   = datetime.now()
        start = end - timedelta(days=30 * months_back)

        # Ambil citra Sentinel-2 / Landsat 8
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(region)
            .filterDate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
        )

        def compute_ndvi(image):
            nir = image.select("B8")
            red = image.select("B4")
            return image.addBands(nir.subtract(red).divide(nir.add(red)).rename("NDVI"))

        ndvi_collection = collection.map(compute_ndvi)
        mean_ndvi = ndvi_collection.select("NDVI").mean()

        stats = mean_ndvi.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=30
        ).getInfo()

        return {
            "region": region_name,
            "ndvi_mean": stats.get("NDVI"),
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
        }

    def compute_change(self, region_name: str) -> dict:
        current  = self.get_ndvi(region_name, months_back=1)
        baseline = self.get_ndvi(region_name, months_back=6)
        change_pct = ((current["ndvi_mean"] - baseline["ndvi_mean"])
                      / baseline["ndvi_mean"] * 100)
        return {
            "region": region_name,
            "ndvi_current": current["ndvi_mean"],
            "ndvi_baseline": baseline["ndvi_mean"],
            "change_pct": round(change_pct, 2),
            "status": "DEFORESTASI" if change_pct < -5 else "NORMAL",
        }
```

**Output Schema:**
```json
{
  "region": "bedugul",
  "ndvi_current": 0.52,
  "ndvi_baseline": 0.60,
  "change_pct": -12.0,
  "status": "DEFORESTASI"
}
```

---

## 📡 Modul 2 — OSINT Social Listener

**Tujuan:** Mengukur Public Awareness Score via analisis sentimen media sosial.

### Keyword Strategy
```python
KEYWORDS = {
    "bedugul": [
        "Bedugul rusak", "Danau Beratan", "hutan Bedugul",
        "alih fungsi Bedugul", "kerusakan Bedugul",
        # filter out: "liburan Bedugul", "wisata Bedugul"
    ],
    "ubud":    ["sawah Ubud", "alih fungsi Ubud", "lingkungan Ubud"],
    "buleleng": ["pantai Buleleng", "mangrove Buleleng"],
}
NOISE_FILTER = ["liburan", "wisata", "hotel", "kuliner", "foto", "promo"]
```

### Twitter/X via Tweepy
```python
# backend/services/twitter_service.py
import tweepy
from config import TWITTER_BEARER_TOKEN

class TwitterService:
    def __init__(self):
        self.client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)

    def search_recent(self, query: str, max_results: int = 100) -> list[dict]:
        # Exclude noise keywords
        exclude_query = " ".join([f"-{kw}" for kw in NOISE_FILTER])
        full_query = f"{query} {exclude_query} lang:id"

        response = self.client.search_recent_tweets(
            query=full_query,
            max_results=max_results,
            tweet_fields=["created_at", "public_metrics", "text"],
        )
        return [tweet.data for tweet in (response.data or [])]
```

### YouTube via YouTube Data API v3
```python
# backend/services/youtube_service.py
from googleapiclient.discovery import build

class YouTubeService:
    def __init__(self, api_key: str):
        self.youtube = build("youtube", "v3", developerKey=api_key)

    def search_videos(self, query: str, max_results: int = 50) -> list[dict]:
        request = self.youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            relevanceLanguage="id",
            maxResults=max_results,
        )
        response = request.execute()
        return response.get("items", [])
```

### NLP Sentiment — IndoBERT
```python
# backend/services/nlp_service.py
from transformers import pipeline

class SentimentService:
    def __init__(self):
        self.classifier = pipeline(
            "text-classification",
            model="indobenchmark/indobert-base-p1",
            tokenizer="indobenchmark/indobert-base-p1",
        )
        # Custom vocabulary bahasa Bali
        self.bali_env_terms = [
            "subak", "awig-awig", "desa adat", "pemali",
            "hutan adat", "pura", "tirta", "ngaben", "tri hita karana"
        ]

    def analyze(self, texts: list[str]) -> dict:
        results = self.classifier(texts, truncation=True, max_length=512)
        env_mentions = sum(
            1 for t in texts
            if any(term in t.lower() for term in self.bali_env_terms)
        )
        # Public Awareness Score: 0-100
        awareness_score = round((env_mentions / max(len(texts), 1)) * 100)
        return {
            "total_posts": len(texts),
            "env_mentions": env_mentions,
            "awareness_score": awareness_score,
            "sentiments": results,
        }
```

---

## ⚖️ Modul 3 — Priority Scoring Engine

**Tujuan:** Menggabungkan skor satelit + OSINT → matriks prioritas 4 kuadran.

### Matriks Prioritas

```
                  NDVI Change (Kerusakan Fisik)
                  Rendah          |   Tinggi
                  ────────────────┼────────────────
Awareness  Tinggi│ KLARIFIKASI    │ PRIORITAS TINGGI
Score            │ INFORMASI      │ (tangani fisik)
           Rendah│ MONITORING     │ 🔴 DARURAT MERAH
                 │ RUTIN          │ (2 masalah!)
```

### Implementasi
```python
# backend/agents/scoring_agent.py
from dataclasses import dataclass
from enum import Enum

class PriorityLevel(str, Enum):
    RED_EMERGENCY    = "DARURAT_MERAH"
    HIGH_PRIORITY    = "PRIORITAS_TINGGI"
    INFO_CORRECTION  = "KLARIFIKASI_INFORMASI"
    ROUTINE_MONITOR  = "MONITORING_RUTIN"

@dataclass
class PriorityResult:
    region: str
    ndvi_change_pct: float
    awareness_score: int
    priority: PriorityLevel
    justification: str
    urgency_rank: int  # 1 = paling urgen

class ScoringAgent:
    NDVI_THRESHOLD     = -5.0   # % change dianggap kerusakan tinggi
    AWARENESS_THRESHOLD = 30    # skor <30 dianggap rendah

    def score(self, ndvi_change: float, awareness: int, region: str) -> PriorityResult:
        high_damage   = ndvi_change < self.NDVI_THRESHOLD
        low_awareness = awareness < self.AWARENESS_THRESHOLD

        if high_damage and low_awareness:
            priority = PriorityLevel.RED_EMERGENCY
            justification = (
                f"NDVI turun {ndvi_change:.1f}% + kesadaran publik hanya "
                f"{awareness}/100. Dua masalah kritis bersamaan."
            )
            rank = 1
        elif high_damage and not low_awareness:
            priority = PriorityLevel.HIGH_PRIORITY
            justification = f"Kerusakan fisik tinggi ({ndvi_change:.1f}%). Komunitas sudah aware — prioritaskan penanganan lapangan."
            rank = 2
        elif not high_damage and low_awareness:
            priority = PriorityLevel.INFO_CORRECTION
            justification = f"Persepsi publik tidak sebanding realita fisik yang masih baik."
            rank = 3
        else:
            priority = PriorityLevel.ROUTINE_MONITOR
            justification = "Kondisi stabil. Lanjutkan pemantauan rutin."
            rank = 4

        return PriorityResult(
            region=region,
            ndvi_change_pct=ndvi_change,
            awareness_score=awareness,
            priority=priority,
            justification=justification,
            urgency_rank=rank,
        )
```

---

## 🕌 Modul 4 — Local Policy Analyzer (THK)

**Tujuan:** Kontekstualisasi temuan dengan Tri Hita Karana dan RTRW Bali.

### Parameter THK
```json
// data/thk_parameters.json
{
  "parahyangan": {
    "label": "Keseimbangan Manusia–Alam Sakral",
    "indicators": [
      "kawasan pura terdampak",
      "hutan adat terganggu",
      "sumber air suci tercemar"
    ],
    "ndvi_threshold": -8.0
  },
  "pawongan": {
    "label": "Keseimbangan Antar Manusia",
    "indicators": [
      "komunitas tidak merespons kolektif",
      "tidak ada gerakan sosial lokal"
    ],
    "awareness_threshold": 20
  },
  "palemahan": {
    "label": "Keseimbangan Manusia–Lingkungan Fisik",
    "indicators": [
      "degradasi ekosistem",
      "alih fungsi lahan",
      "pencemaran sungai"
    ],
    "ndvi_threshold": -5.0
  }
}
```

### Implementasi
```python
# backend/agents/policy_agent.py
import json
from pathlib import Path

class PolicyAgent:
    def __init__(self):
        self.thk = json.loads(Path("data/thk_parameters.json").read_text())

    def analyze(self, ndvi_change: float, awareness_score: int) -> dict:
        violations = []

        # Parahyangan check
        if ndvi_change < self.thk["parahyangan"]["ndvi_threshold"]:
            violations.append({
                "dimension": "Parahyangan",
                "status": "TERLANGGAR",
                "detail": "Kawasan sakral/hutan adat berpotensi terdampak deforestasi.",
            })

        # Pawongan check
        if awareness_score < self.thk["pawongan"]["awareness_threshold"]:
            violations.append({
                "dimension": "Pawongan",
                "status": "TERLANGGAR",
                "detail": "Komunitas tidak merespons secara kolektif — gap sosial terdeteksi.",
            })

        # Palemahan check
        if ndvi_change < self.thk["palemahan"]["ndvi_threshold"]:
            violations.append({
                "dimension": "Palemahan",
                "status": "TERLANGGAR",
                "detail": f"Degradasi ekosistem fisik signifikan ({ndvi_change:.1f}% NDVI).",
            })

        return {
            "thk_violations": violations,
            "rtrw_note": "Cek Perda Bali No. 2/2023 terkait kawasan lindung.",
            "recommendation": self._generate_recommendation(violations),
        }

    def _generate_recommendation(self, violations: list) -> str:
        if not violations:
            return "Kondisi sesuai parameter THK. Pertahankan."
        dims = [v["dimension"] for v in violations]
        return (
            f"Pelanggaran nilai {', '.join(dims)} terdeteksi. "
            "Koordinasikan dengan bendesa adat dan Dinas LHK Bali."
        )
```

---

## 🧠 Agen Orkestrator

**Tujuan:** Mengkoordinasikan semua modul secara berurutan dan menghasilkan laporan final.

```python
# backend/agents/orchestrator.py
from agents.satellite_agent import SatelliteAgent
from agents.osint_agent import OSINTAgent
from agents.scoring_agent import ScoringAgent
from agents.policy_agent import PolicyAgent

class PEMALIOrchestrator:
    def __init__(self):
        self.satellite = SatelliteAgent()
        self.osint     = OSINTAgent()
        self.scoring   = ScoringAgent()
        self.policy    = PolicyAgent()

    def run_audit(self, region: str) -> dict:
        print(f"[PEMALI] Memulai audit wilayah: {region}")

        # Modul 1 — Satellite
        satellite_data = self.satellite.compute_change(region)
        ndvi_change = satellite_data["change_pct"]

        # Modul 2 — OSINT
        osint_data     = self.osint.run(region)
        awareness      = osint_data["awareness_score"]

        # Modul 3 — Scoring
        priority_result = self.scoring.score(ndvi_change, awareness, region)

        # Modul 4 — Policy/THK
        policy_result  = self.policy.analyze(ndvi_change, awareness)

        return {
            "region": region,
            "satellite": satellite_data,
            "osint": osint_data,
            "priority": priority_result.__dict__,
            "policy": policy_result,
            "generated_at": datetime.utcnow().isoformat(),
        }
```

---

## 🌐 API Endpoints (FastAPI)

```python
# backend/main.py
from fastapi import FastAPI
from agents.orchestrator import PEMALIOrchestrator

app = FastAPI(title="PEMALI API", version="0.1.0")
orchestrator = PEMALIOrchestrator()

@app.get("/audit/{region}")
async def run_audit(region: str):
    """Jalankan audit lengkap untuk satu wilayah."""
    return orchestrator.run_audit(region)

@app.get("/audit/all")
async def run_all_audits():
    """Audit semua wilayah pilot sekaligus."""
    regions = ["bedugul", "ubud", "buleleng"]
    return [orchestrator.run_audit(r) for r in regions]

@app.get("/regions")
async def list_regions():
    """Daftar wilayah yang dipantau."""
    return {"regions": ["bedugul", "ubud", "buleleng"]}

@app.get("/health")
async def health():
    return {"status": "ok", "system": "PEMALI v0.1"}
```

---

## 📊 Frontend Dashboard (Next.js)

**Key Components:**

```tsx
// frontend/components/MapHeatmap.tsx
// Visualisasi NDVI heatmap per wilayah menggunakan Leaflet.js atau Mapbox GL

// frontend/components/ScoreCard.tsx
// Menampilkan priority level (DARURAT MERAH / PRIORITAS TINGGI / dll)
// dengan warna: RED / ORANGE / YELLOW / GREEN

// frontend/pages/index.tsx
// Dashboard utama: peta Bali + kartu skor + tabel urgensi wilayah
```

**Routing:**
- `/` → Dashboard peta + overview semua wilayah
- `/report/[region]` → Laporan audit detail per wilayah
- `/api/audit/[region]` → Proxy ke backend FastAPI

---

## 📅 Timeline 13 Hari

| Hari | Person A (Satelit + Agent) | Person B (OSINT + Frontend) | Milestone |
|---|---|---|---|
| 1–2 | Setup repo, skeleton arsitektur | Setup repo, skeleton OSINT pipeline | Arsitektur & API koneksi terdefinisi |
| 3–5 | Build Modul Satelit, query NDVI 3 wilayah | Build Modul OSINT, sentiment pipeline | Modul 1 & 2 berdiri sendiri |
| 6–7 | Integrasi Modul 1+2 ke Agen Orkestrator | Build Modul Prioritas (logic layer) | Agen Orkestrator aktif |
| 8–9 | Build Modul Analisis Kebijakan THK | Mulai build dashboard Next.js | Semua 4 modul selesai |
| 10–11 | End-to-end integration testing | Dashboard: peta interaktif + visualisasi | Full system terintegrasi |
| 12 | E2E testing dengan data real Bedugul | Polish UI dashboard | Prototype siap demo |
| 13 | Buffer: bug fixing, dokumentasi | Buffer: polish demo | ✅ DEMO READY |

> ⚠️ **Catatan Kritis:** Modul OSINT adalah yang paling berisiko jadi blocker karena keterbatasan API Instagram dan TikTok. **Keputusan approach OSINT harus dibuat di Hari 1** — jangan di-delay.

---

## 📦 Dependencies (`requirements.txt`)

```txt
# Core
fastapi==0.110.0
uvicorn[standard]==0.29.0
pydantic==2.6.0
python-dotenv==1.0.0

# Google Earth Engine
earthengine-api==0.1.390

# OSINT
tweepy==4.14.0
google-api-python-client==2.124.0

# NLP
transformers==4.40.0
torch==2.2.0
sentencepiece==0.2.0

# Database
sqlalchemy==2.0.29
aiosqlite==0.20.0
# psycopg2-binary==2.9.9  # uncomment for PostgreSQL

# Agent Framework (pilih salah satu)
langchain==0.1.16
# crewai==0.28.0

# Utils
httpx==0.27.0
pandas==2.2.0
```

---

## ✅ Development Checklist

### Infrastruktur
- [ ] Repo setup dengan struktur folder di atas
- [ ] `.env` dikonfigurasi dengan semua API keys
- [ ] Google Earth Engine Service Account aktif
- [ ] Database schema dibuat (`pemali.db`)
- [ ] FastAPI server bisa dijalankan (`uvicorn main:app --reload`)

### Modul 1 — Satellite
- [ ] GEE API bisa di-query (`earthengine-api` auth berhasil)
- [ ] NDVI untuk 3 wilayah pilot bisa dihitung
- [ ] Change detection (baseline vs current) berfungsi
- [ ] Output JSON sesuai schema

### Modul 2 — OSINT
- [ ] Tweepy berhasil search tweets
- [ ] YouTube search berhasil
- [ ] IndoBERT sentiment pipeline berjalan
- [ ] Public Awareness Score dihitung dengan benar

### Modul 3 — Scoring
- [ ] Matriks 4 kuadran berfungsi untuk semua kombinasi input
- [ ] Urgency ranking benar (DARURAT MERAH = rank 1)
- [ ] Justifikasi teks dihasilkan otomatis

### Modul 4 — Policy/THK
- [ ] Parameter THK dibaca dari `thk_parameters.json`
- [ ] Semua 3 dimensi (Parahyangan, Pawongan, Palemahan) dicek
- [ ] Rekomendasi ke desa adat dihasilkan

### Integrasi & Frontend
- [ ] Orkestrator memanggil semua 4 modul secara berurutan
- [ ] API endpoint `/audit/{region}` mengembalikan laporan lengkap
- [ ] Dashboard Next.js menampilkan data dari API
- [ ] Heatmap peta NDVI divisualisasikan
- [ ] E2E test dengan data real Bedugul berhasil

---

## 📚 Referensi Teknis

- [Google Earth Engine Python API Docs](https://developers.google.com/earth-engine/guides/python_install)
- [Tweepy Documentation](https://docs.tweepy.org/)
- [YouTube Data API v3](https://developers.google.com/youtube/v3)
- [IndoBERT — HuggingFace](https://huggingface.co/indobenchmark/indobert-base-p1)
- [LangChain Docs](https://python.langchain.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js 14 Documentation](https://nextjs.org/docs)

---

*PEMALI Development Documentation — Disiapkan paralel dengan esai lomba Festival Pelajar Ajeg Bali Ke-4 2026*  
*Deadline sistem: 13 Hari | Deadline esai: 14 Mei 2026, 23.59 WITA*
