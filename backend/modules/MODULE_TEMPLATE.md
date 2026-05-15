---
# ═══════════════════════════════════════════════════════
# MACHINE-READABLE MANIFEST — dibaca registry & AI agent
# ═══════════════════════════════════════════════════════

module_name        : "nama_modul_kamu"       # snake_case, unique di sistem
version            : "1.0.0"                  # semver
tags               : ["water", "sensor"]      # lihat daftar tag di bawah
depends_on         : []                       # list module name yang jadi dependency
input_schema       : "NamaInputModel"         # nama kelas Pydantic input
requires_env       : []                       # env vars wajib: ["API_KEY_X", "DB_URL"]
requires_network   : false                    # apakah modul ini hit API eksternal?
requires_db        : false                    # apakah modul ini akses PostgreSQL?
external_apis      : []                       # URL API eksternal: ["https://api.data.go.id"]
rate_limit_rps     : null                     # rate limit request per detik (null = no limit)
timeout_ms         : 30000                    # estimasi timeout eksekusi
author             : "nama_kamu <email>"
created            : "2026-05-15"
last_updated       : "2026-05-15"
---

# Modul: [NAMA_MODUL]

> **Status**: draft / review / production
> **Tag**: lihat daftar tag di atas

---

## 1. Deskripsi

_Jelaskan dalam 2-3 paragraf: apa yang modul ini lakukan, data apa yang dihasilkan,
kapan harus dipakai, dan konteks penggunaannya dalam ekosistem audit lingkungan PEMALI._

Contoh:

```
Modul ini mengambil data kualitas air real-time dari API BMKG/BBWS untuk
lokasi sungai di Bali. Data yang dihasilkan mencakup pH, turbidity, DO
(dissolved oxygen), dan indeks pencemaran. Cocok digunakan oleh water_agent
untuk audit kualitas air periodik atau investigasi laporan pencemaran.
```

---

## 2. Input Schema

| Parameter        | Type   | Required | Default  | Description                                           |
|------------------|--------|----------|----------|-------------------------------------------------------|
| `river_name`     | str    | ✅        | -        | Nama sungai, e.g. "Tukad Ayung", "Tukad Badung"       |
| `date_from`      | str    | ❌        | `null`   | ISO date YYYY-MM-DD. Default = 7 hari terakhir         |
| `metrics`        | list   | ❌        | `["all"]`| Pilihan: `["ph", "turbidity", "do", "pollution_index"]`|

```python
class MyInputModel(BaseModel):
    river_name: str = Field(..., description="Nama sungai target")
    date_from: Optional[str] = Field(default=None, description="ISO date")
    metrics: List[str] = Field(default_factory=lambda: ["all"])
```

> **Rule**: setiap field input WAJIB punya `description` — ini dibaca LLM untuk menentukan parameter.

---

## 3. Output Schema

### Success (`status=200`)

```json
{
  "status": 200,
  "data": {
    "river_name": "Tukad Ayung",
    "ph": 7.2,
    "turbidity_ntu": 12.4,
    "dissolved_oxygen_mg_l": 6.1,
    "pollution_index": "light",
    "sample_count": 15,
    "fetched_at": "2026-05-15T14:30:00Z"
  },
  "agent_hint": "Kualitas air Tukad Ayung baik. pH normal 7.2, turbidity 12.4 NTU (batas aman), DO 6.1 mg/L. Pollusi ringan. Tidak ada anomali yang perlu tindakan.",
  "thk_alignment": {
    "parahyangan": "Data kualitas air dikumpulkan langsung dari sensor BMKG tanpa modifikasi",
    "pawongan": "Hasil pantauan dapat diakses oleh Dinas Lingkungan Hidup dan masyarakat",
    "palemahan": "Monitoring rutin membantu deteksi dini pencemaran sungai di Bali"
  }
}
```

### Error (`status=400` atau `500`)

```json
{
  "status": 400,
  "data": {},
  "agent_hint": "Nama sungai 'Xyz' tidak ditemukan di database. Coba periksa ejaan atau gunakan nama resmi.",
  "error_msg": "River not found: 'Xyz'. Available: Tukad Ayung, Tukad Badung, Tukad Petanu.",
  "thk_alignment": null
}
```

---

## 4. THK Alignment Guidelines

_Setiap modul WAJIB mengisi `thk_alignment`. Gunakan sebagai panduan:_

| Pilar         | Arti                                     | Contoh isian                                                   |
|---------------|------------------------------------------|----------------------------------------------------------------|
| parahyangan   | Integritas, kebenaran data, etika        | "Data dikumpulkan tanpa manipulasi — murni dari sensor"         |
| pawongan      | Transparansi, kolaborasi, keadilan       | "Hasil audit dapat diakses oleh pemangku kepentingan terkait"   |
| palemahan     | Dampak lingkungan, keberlanjutan         | "Monitoring rutin mencegah kerusakan lingkungan yang tidak terdeteksi" |

**Preset shortcut** (dari `THKPresets` di `base_module.py`):

```python
from backend.core.base_module import THKPresets

# Untuk modul sensor lingkungan
thk = THKPresets.environmental_sensor("Nama Sensor", "Lokasi")

# Untuk modul pengolahan data
thk = THKPresets.data_processing("Sumber Data")

# Untuk modul penjadwalan otonom
thk = THKPresets.autonomous_task("Deskripsi Task")
```

> Kalau use-case mu tidak masuk preset, tulis manual. Yang penting ketiga field TERISI.

---

## 5. `agent_hint` Guidelines

`agent_hint` adalah **narasi singkat untuk AI agent** setelah terima data modul. Fungsinya:

- Jelaskan MAKNA data (bukan sekadar deskripsi mentah)
- Beri REKOMENDASI langkah selanjutnya
- Sebutkan ANOMALI jika ada
- Bahasa: **Indonesia natural**, 1-3 kalimat

**Template isian:**

```
Jika sukses:
"[Ringkasan data]. [Interpretasi]. [Rekomendasi jika ada]."

Jika error:
"Gagal [aksi]. [Penyebab singkat]. [Saran perbaikan untuk agent]."
```

**Contoh baik:**
```
"NDVI di Gianyar turun 0.15 poin dari audit bulan lalu. Ini bisa tanda deforestasi.
Rekomendasi: cross-check dengan satellite_imagery untuk konfirmasi visual."
```

**Contoh buruk:**
```
"Data tersedia."
"Success."
"OK"
```

---

## 6. Error Handling Pattern

```python
from backend.core.base_module import ModuleOutput

async def execute(self, params, context) -> ModuleOutput:
    start_ms = self._now_ms()

    try:
        # --- logic utama ---
        result = await fetch_data(params)

        return ModuleOutput(
            status=200,
            data=result,
            agent_hint=f"Data berhasil diambil. {len(result)} records dari {params.location}.",
            thk_alignment=THKPresets.environmental_sensor(self.name, params.location),
        )

    except ValueError as e:
        # Error yang bisa di-recover agent (recoverable)
        return ModuleOutput(
            status=400,
            data={},
            error_msg=str(e),
            agent_hint=f"Parameter tidak valid: {e}. Coba sesuaikan input dan ulangi.",
        )

    except ConnectionError as e:
        # Error upstream — agent bisa retry
        return ModuleOutput(
            status=503,
            data={},
            error_msg=str(e),
            agent_hint=f"API eksternal tidak merespons. Coba lagi dalam beberapa saat.",
        )

    except Exception as e:
        # Error tak terduga — agent tidak bisa recover sendiri
        return ModuleOutput(
            status=500,
            data={},
            error_msg=f"Unexpected: {e}",
            agent_hint="Error internal. Laporkan ke tim atau coba dengan parameter berbeda.",
        )
```

**Status code convention:**
| Status | Arti                    | Agent Action                |
|--------|-------------------------|-----------------------------|
| 200    | OK                      | Lanjut / selesai             |
| 400    | Parameter tidak valid   | Sesuaikan parameter, retry   |
| 404    | Resource tidak ditemukan| Cari resource alternatif     |
| 408    | Timeout eksternal       | Retry dengan timeout lebih besar |
| 429    | Rate limited            | Tunggu, retry                |
| 500    | Internal error          | Laporkan, jangan retry       |
| 503    | Upstream tidak tersedia | Retry nanti                  |

---

## 7. Lifecycle Hooks

```python
class MyModule(PemaliModuleV2):

    async def setup(self, context: Dict[str, Any]) -> None:
        """Dipanggil SEKALI saat modul pertama kali di-load."""
        self._http = aiohttp.ClientSession()
        self._cache = {}

    async def execute(self, params, context) -> ModuleOutput:
        # setup() sudah dipanggil sebelum ini
        ...

    async def teardown(self, context: Dict[str, Any]) -> None:
        """Dipanggil SEKALI saat modul di-unload / sistem shutdown."""
        await self._http.close()
```

> `setup()` dan `teardown()` opsional. Default: no-op. Registry memanggil `setup()` saat module pertama di-load.

---

## 8. Testing Convention

**Lokasi**: `backend/tests/modules/test_[nama_modul].py`

**Minimum test cases** (3):
1. **Success path** — parameter valid, cek return `status=200` dan `agent_hint` tidak kosong
2. **Invalid params** — parameter tidak valid, cek return `status=400`
3. **THK compliance** — cek `thk_alignment` tidak None dan semua field terisi

```python
import pytest
from backend.modules.my_module import MyModule, MyInput

@pytest.mark.asyncio
async def test_my_module_success():
    mod = MyModule()
    params = MyInput(river_name="Tukad Ayung")
    result = await mod.execute(params, {"session_id": "test"})
    
    assert result.status == 200
    assert len(result.data) > 0
    assert result.agent_hint != ""
    assert result.thk_alignment is not None
    assert result.thk_alignment.parahyangan
    assert result.thk_alignment.pawongan
    assert result.thk_alignment.palemahan

@pytest.mark.asyncio
async def test_my_module_invalid_params():
    mod = MyModule()
    with pytest.raises(Exception):
        MyInput(river_name="")  # Pydantic validation

@pytest.mark.asyncio
async def test_my_module_thk_compliance():
    mod = MyModule()
    params = MyInput(river_name="Tukad Ayung")
    result = await mod.execute(params, {"session_id": "test"})
    
    assert result.thk_alignment is not None
    assert len(result.thk_alignment.parahyangan) > 0
    assert len(result.thk_alignment.pawongan) > 0
    assert len(result.thk_alignment.palemahan) > 0
```

---

## 9. Tag System

Tag digunakan untuk auto-scoping: agent mana yang boleh panggil modul ini.

| Tag           | Ditujukan untuk  | Deskripsi                                |
|---------------|------------------|------------------------------------------|
| `geo`         | geo_agent        | Data spasial, satelit, GIS              |
| `water`       | water_agent      | Kualitas air, hidrologi, DAS            |
| `fire`        | fire_agent       | Titik api, hotspot, indeks kekeringan    |
| `osint`        | osint_agent       | Berita, media sosial, scraping          |
| `scheduler`   | scheduler_agent  | Penjadwalan task otonom                  |
| `climate`     | -                | Cuaca, curah hujan, iklim               |
| `culture`     | -                | Kearifan lokal, adat, subak             |
| `environment` | umum             | Lintas-agent: NDVI, tutupan lahan       |
| `testing`     | -                | Modul untuk testing/development saja     |
| `utility`     | -                | Modul bantu: logging, notifikasi, dll    |

Modul bisa punya **multiple tag**.

---

## 10. Submission Checklist

Sebelum submit PR/modul, pastikan semua ini beres:

- [ ] File diletakkan di `backend/modules/[nama_modul].py`
- [ ] Nama file = nama modul (snake_case)
- [ ] Class inherit `PemaliModuleV2`
- [ ] `@property name` → unique, snake_case
- [ ] `@property version` → semver
- [ ] `@property description` → Indonesia, deskriptif
- [ ] `@property tags` → minimal 1 tag dari tabel di atas
- [ ] `@property input_schema` → Pydantic BaseModel dengan `Field(description=...)`
- [ ] `@property output_example` → Dict dengan contoh sukses & error
- [ ] `execute()` → return `ModuleOutput(status=200, ..., agent_hint=..., thk_alignment=...)`
- [ ] `agent_hint` → tidak kosong, naratif, informatif
- [ ] `thk_alignment` → ketiga field terisi (gunakan `THKPresets` jika cocok)
- [ ] Error handling → `try/except` dengan agent_hint error yang membantu
- [ ] Testing → minimal 3 test di `backend/tests/modules/test_[nama_modul].py`
- [ ] Tidak ada hardcoded secret/API key (gunakan environment variable)
- [ ] Tidak ada komentar berbahasa Inggris (kecuali docstring public function)

---

## 11. Quick Start

```bash
# 1. Copy template
cp backend/modules/_example_well_documented.py backend/modules/my_new_module.py

# 2. Edit:
#    - Ganti nama class
#    - Ganti @property name, description, tags
#    - Ganti input_schema (Pydantic model mu)
#    - Isi execute() dengan logic mu
#    - Update output_example
#    - Update THK alignment sesuai konteks

# 3. Test
pytest backend/tests/modules/test_my_new_module.py -v

# 4. Verifikasi ter-load
python -c "from backend.core.registry import registry; print(list(registry.tools.keys()))"
# Output harus mengandung 'my_new_module'

# 5. Submit PR
```

---

## 12. Folder Layout untuk Modul Kompleks

Kalau modul kamu butuh lebih dari 1 file (utility, constants, sub-models):

```
backend/modules/
├── my_module/
│   ├── __init__.py          # import & expose MyModule class
│   ├── module.py            # class MyModule(PemaliModuleV2)
│   ├── schemas.py           # Pydantic models tambahan
│   ├── client.py            # HTTP client / API wrapper
│   └── utils.py             # helper functions
└── MODULE_TEMPLATE.md       # panduan ini (jangan dihapus)
```

> Folder modul TETAP perlu file `module.py` dengan class utama yang inherit `PemaliModuleV2`.

---

## 13. AI Agent Perspective

Ini yang dibaca oleh AI agent saat menerima modul kamu:

| Agen lihat...        | Dari mana...                              | Gunanya...                           |
|----------------------|-------------------------------------------|---------------------------------------|
| nama tool            | `manifest["name"]`                        | identifier buat function calling      |
| deskripsi            | `manifest["description"]`                 | kapan & kenapa pakai tool ini         |
| parameter            | `manifest["parameters"]`                  | JSON Schema buat validasi argumen     |
| versi                | `manifest["version"]`                     | tracking breaking changes             |
| tag                  | `manifest["tags"]`                        | scoping: agent mana yang boleh panggil|
| contoh output        | `manifest["output_example"]`              | ekspektasi bentuk return value        |
| agent_hint (runtime) | `ModuleOutput.agent_hint`                 | interpretasi langsung untuk agent     |
| THK (runtime)        | `ModuleOutput.thk_alignment`              | alignment etis hasil audit            |

> **Rule**: tulis `description` seolah-olah kamu jelasin ke kolega — bukan ke compiler. Agent pakai natural language understanding.

---

## 14. FAQ

**Q: Gimana kalau modulku gak selesai dalam 1x panggil (long-running)?**
A: Return `status=200` dengan `data.status = "processing"` dan `agent_hint` yang menyuruh agent cek lagi nanti. Atau pakai `system_scheduler` untuk re-check otomatis.

**Q: Boleh return data yang partially complete?**
A: Boleh, tapi sebutkan di `agent_hint` bagian mana yang incomplete dan kenapa.

**Q: Gimana cara share context antar modul?**
A: Gunakan `depends_on` di property modul. Registry akan passing output modul dependency sebagai `context["shared_data"]`.

**Q: Modul gak perlu THK alignment karena cuma utility?**
A: Tetap isi. Utility pun punya dampak ke integritas sistem (parahyangan), akses tim (pawongan), dan efisiensi resource komputasi (palemahan).
