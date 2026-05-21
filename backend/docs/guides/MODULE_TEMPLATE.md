# 🧩 PEMALI Module Development Guide (V2.6 Standard)

Selamat datang di ekosistem PEMALI! Panduan ini dirancang agar kontributor (manusia) dan AI Coding Assistant dapat membangun modul baru dengan standar yang seragam, aman, dan efisien.

## 🧠 Filosofi: "Pure Data Collector"
Modul di PEMALI **TIDAK PERLU** melakukan penalaran, narasi, atau analisis THK di dalam kode. Modul adalah **Indra (Sensor)** dan **Tangan (Aktuator)**. 

- **Tugas Modul**: Mengambil data teknis mentah (JSON) seakurat mungkin atau menjalankan aksi fisik.
- **Tugas Orchestrator**: Mengolah data tersebut (Cognition) menjadi laporan atau keputusan otonom.

---

## 🛠 Aturan Emas (UTI V2)
1.  **Inherit `PemaliModuleV2`**: Wajib sebagai basis kelas agar terdeteksi otomatis oleh `Registry`.
2.  **Pydantic `input_schema`**: Parameter input modul wajib menggunakan `BaseModel` agar tervalidasi otomatis sebelum eksekusi.
3.  **Async Execute**: Semua proses (I/O, API, DB) wajib menggunakan `async def execute`.
4.  **Return `ModuleOutput`**: Standar tunggal output sistem yang mengandung `status` (int), `data` (dict), dan `error_msg` (str).

---

## 📝 Boilerplate Template (Recommended Style)

Copy-paste kode ini ke file baru di folder `/modules/` (misal: `modules/sensor_tanah_mod.py`):

```python
import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field
from core.base_module import PemaliModuleV2, ModuleOutput

# 1. Definisikan Input Schema
# Field 'description' sangat krusial karena akan dibaca oleh AI Agent sebagai panduan.
class MyModuleInput(BaseModel):
    lokasi: str = Field(..., description="Nama wilayah koordinat atau nama tempat.")
    radius: int = Field(default=500, description="Radius pencarian dalam satuan meter.")

# 2. Definisikan Class Modul
class MyNewModule(PemaliModuleV2):
    @property
    def name(self) -> str:
        return "my_module_snake_case" # Identitas unik modul

    @property
    def description(self) -> str:
        # Jelaskan kaitan modul ini dengan tugas lingkungan (Satellite/OSINT/Policy)
        return "Mendeskripsikan fungsi modul ini secara mendalam untuk reasoning AI."

    @property
    def input_schema(self):
        return MyModuleInput

    async def execute(self, params: MyModuleInput, context: Dict[str, Any]) -> ModuleOutput:
        # Konteks sistem (seperti session_id) dikirim otomatis oleh Orchestrator
        session_id = context.get("session_id", "unknown")
        
        try:
            # --- LOGIKA TEKNIS ANDA DI SINI ---
            # Contoh: result = await panggil_api_sensor(params.lokasi)
            
            return ModuleOutput(
                status=200,
                data={
                    "lokasi": params.lokasi,
                    "status": "active",
                    "value": 85.5,
                    "unit": "percentage",
                    "processed_at": str(datetime.datetime.now())
                }
            )
        except Exception as e:
            # Error message akan digunakan AI untuk melakukan Self-Correction (Retry)
            return ModuleOutput(status=500, error_msg=str(e))
```

---

## 🤖 AI Prompt Kit (Untuk Pengguna AI)
Jika Anda menggunakan AI (ChatGPT/Claude/Antigravity) untuk membuat modul baru, gunakan prompt berikut untuk hasil terbaik:

> "Buatlah modul PEMALI V2 Python. Modul ini harus inherit dari `PemaliModuleV2` dan menggunakan `ModuleOutput`. Gunakan gaya `@property` untuk `name`, `description`, dan `input_schema`. Fungsi `execute` harus async dan menerima argumen `(self, params: BaseModel, context: Dict[str, Any])`. 
> 
> **Spesifikasi Modul:**
> Tujuan: [Sebutkan tujuan modul, misal: Ambil data kualitas udara]
> Input: [Sebutkan parameter, misal: latitude, longitude]
> Output: [Sebutkan data yang diharapkan, misal: AQI index, PM2.5]"

---

## 📋 Checklist Validasi
- [ ] Nama file berakhiran `_mod.py` (untuk auto-discovery).
- [ ] Tidak ada logika `agent_hint` atau `thk_alignment` (Deprecated).
- [ ] Semua I/O menggunakan `async`.
- [ ] Pydantic fields memiliki `description` yang manusiawi.
