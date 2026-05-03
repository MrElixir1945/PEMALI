# Panduan Membuat Modul PEMALI (UTI Standard)

File ini adalah panduan cepat bagi developer atau kontributor yang ingin menambahkan kemampuan baru (*Tools/Skills*) ke dalam sistem PEMALI AI Agent.

Sistem PEMALI menggunakan arsitektur **Auto-Discovery**. Anda **TIDAK PERLU** mengedit file inti (seperti `orchestrator.py` atau `main.py`). Cukup buat satu file Python di dalam folder `/modules/` dan ikuti aturan *Unified Tool Interface* (UTI) di bawah ini.

## 4 Aturan Emas Pembuatan Modul

1. **Turunan `PemaliModule`**: Wajib *inherit* dari `PemaliModule` agar file dikenali oleh *registry* sistem.
2. **Definisikan `manifest`**: *Property* ini berisi JSON schema untuk mendeskripsikan *tool* ke AI Agent (nama, deskripsi fungsi, parameter yang dibutuhkan).
3. **Gunakan `async def execute`**: Fungsi utama untuk memproses logika Anda. Wajib bersifat asinkron (`async`).
4. **Kembalikan `ModuleOutput`**: Fungsi wajib mereturn objek `ModuleOutput` (yang mendefinisikan `status`, `data`, `agent_hint`, dan `thk_alignment`).

---

## 📝 Boilerplate Template (Copy-Paste Ini)

Buat file baru berakhiran `.py` di dalam folder `/modules/` (misal: `modules/cuaca_mod.py`) dan tempelkan kode berikut:

```python
import asyncio
from typing import Dict, Any
from core.base_module import PemaliModule, ModuleOutput

class TemplateModulBaru(PemaliModule):
    
    @property
    def manifest(self) -> Dict[str, Any]:
        """
        Metadata untuk memperkenalkan tool ke AI Agent.
        AI akan membaca ini untuk memutuskan kapan harus memanggil modul Anda.
        """
        return {
            "name": "nama_modul_unik", # WAJIB: Huruf kecil & underscore (snake_case)
            "description": "Jelaskan dengan SANGAT DETAIL kapan AI harus memakai alat ini dan apa fungsinya.",
            "parameters": {
                "type": "object",
                "properties": {
                    # Definisikan parameter input yang Anda inginkan dari AI Agent
                    "lokasi": {
                        "type": "string", 
                        "description": "Nama lokasi yang ingin dicek"
                    },
                },
                "required": ["lokasi"] # Daftar parameter yang wajib diisi AI
            }
        }

    async def execute(self, params: Dict[str, Any]) -> ModuleOutput:
        """Logika Utama Modul Anda"""
        try:
            # 1. Ambil argumen/input yang diberikan oleh AI Agent
            lokasi = params.get("lokasi", "Tidak diketahui")
            
            # 2. TULIS LOGIKA KERJA DI SINI
            # Contoh: Panggil API eksternal, scrape web, atau hitung matematika
            # await asyncio.sleep(1) # Simulasi I/O
            hasil_mentah = {"lokasi": lokasi, "status_cuaca": "Hujan deras"}
            
            # 3. Kembalikan output sesuai standar UTI
            return ModuleOutput(
                status="success",
                data=hasil_mentah, # Data mentah untuk disimpan ke database
                agent_hint=f"Cuaca di {lokasi} saat ini hujan deras. Sarankan untuk menunda aktivitas luar ruangan.", # Hint manusiawi agar AI paham
                thk_alignment="Palemahan" # Pilih: Parahyangan / Pawongan / Palemahan
            )
            
        except Exception as e:
            # 4. Tangani error agar sistem utama (Orchestrator) tidak ikut crash
            return ModuleOutput(
                status="error", 
                data={"error_detail": str(e)}, 
                agent_hint="Gagal mengambil data cuaca karena terjadi kesalahan internal server.",
                thk_alignment="Netral"
            )
```

## Penjelasan `ModuleOutput` (Sangat Penting!)
*   **`data`**: *Payload* teknis murni (JSON/Dict). Ini akan disimpan ke database (*State Manager*). **AI Agent tidak akan membaca bagian ini secara langsung** untuk menghemat token.
*   **`agent_hint`**: Kesimpulan singkat (*human-readable*). **Ini yang dibaca oleh AI Agent**. Jadikan ini seperti pesan dari sistem ke AI.
*   **`thk_alignment`**: Analisis wajib terkait filosofi *Tri Hita Karana*. Parameter ini krusial untuk pelaporan kebijakan.
