# Panduan Membuat Modul PEMALI (V2 Standard)

File ini adalah panduan cepat bagi developer atau kontributor yang ingin menambahkan kemampuan baru (*Tools/Skills*) ke dalam sistem PEMALI AI Agent.

Sistem PEMALI menggunakan arsitektur **Auto-Discovery**. Anda **TIDAK PERLU** mengedit file inti (seperti `orchestrator.py` atau `registry.py`). Cukup buat satu file Python di dalam folder `/modules/` dan ikuti aturan *Unified Tool Interface* (UTI) V2 di bawah ini.

## 4 Aturan Emas Pembuatan Modul V2

1. **Turunan `PemaliModuleV2`**: Wajib *inherit* dari `PemaliModuleV2` agar file dikenali oleh *registry* sistem.
2. **Definisikan `input_schema` Pydantic**: Parameter input modul harus menggunakan `pydantic.BaseModel` agar tervalidasi otomatis.
3. **Gunakan `async def execute(self, params, context)`**: Fungsi utama untuk memproses logika Anda. Wajib bersifat asinkron (`async`).
4. **Kembalikan `ModuleOutput` V2**: Fungsi wajib mereturn objek `ModuleOutput` (yang mendefinisikan `status` dengan kode HTTP-style, `data`, dan `error_msg`).

---

## 📝 Boilerplate Template (Copy-Paste Ini)

Buat file baru berakhiran `.py` di dalam folder `/modules/` (misal: `modules/cuaca_mod.py`) dan tempelkan kode berikut:

```python
import asyncio
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from core.base_module import PemaliModuleV2, ModuleOutput

# 1. Definisikan Schema Input (Pydantic)
# AI akan membaca schema ini untuk mengetahui parameter apa saja yang dibutuhkan.
class CuacaInput(BaseModel):
    lokasi: str = Field(..., description="Nama lokasi yang ingin dicek cuacanya")

# 2. Buat Class Modul Turunan dari PemaliModuleV2
class TemplateModulBaru(PemaliModuleV2):
    # WAJIB: Huruf kecil & underscore (snake_case)
    name = "cek_cuaca" 
    
    # WAJIB: Jelaskan dengan SANGAT DETAIL kapan AI harus memakai alat ini dan apa fungsinya.
    description = "Mengecek informasi cuaca berdasarkan nama lokasi yang diberikan." 
    
    # Hubungkan schema yang sudah dibuat di atas
    input_schema = CuacaInput
    
    # Opsional: Jika modul ini bergantung pada modul lain dalam DAG (Directed Acyclic Graph)
    depends_on: List[str] = [] 
    
    async def execute(self, params: CuacaInput, context: Dict[str, Any]) -> ModuleOutput:
        """Logika Utama Modul Anda"""
        try:
            # 1. Parameter sudah tervalidasi otomatis. Anda bisa langsung pakai.
            lokasi = params.lokasi
            session_id = context.get("session_id", "default_session")
            
            # 2. TULIS LOGIKA KERJA DI SINI
            # Contoh: Panggil API eksternal, scrape web, atau hitung matematika
            # await asyncio.sleep(1) # Simulasi I/O
            hasil_mentah = {
                "lokasi": lokasi, 
                "status_cuaca": "Hujan deras",
                "session": session_id
            }
            
            # 3. Kembalikan output sesuai standar ModuleOutput V2
            return ModuleOutput(
                status=200,           # 200 = OK
                data=hasil_mentah,    # Data mentah untuk disimpan / diproses lebih lanjut
                error_msg=None        # Tidak ada error
            )
            
        except Exception as e:
            # 4. Tangani error agar Self-Correction AI dapat mengevaluasi ulang
            return ModuleOutput(
                status=500,           # 500 = Internal Server Error / 400 = Bad Request
                data={}, 
                error_msg=str(e)      # Pesan error akan diteruskan ke AI untuk diperbaiki
            )
```

## Penjelasan `ModuleOutput` (V2 Standard)
*   **`status`**: Kode status bergaya HTTP (contoh: 200 untuk Sukses, 400 untuk Validasi Parameter Gagal, 500 untuk Error Internal). AI menggunakan kode ini untuk tahu apakah eksekusinya berhasil.
*   **`data`**: *Payload* teknis murni (JSON/Dict). Ini berisi hasil langsung dari alat yang akan dibaca oleh agen AI.
*   **`error_msg`**: Jika status != 200, isikan alasan spesifik di sini. Fitur **Self-Correction AI** akan membaca `error_msg` untuk melakukan perbaikan argumen. Jika sukses, biarkan `None`.
