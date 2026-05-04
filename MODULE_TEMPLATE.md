# Protokol Ekstensi Modul Terpadu PEMALI (Spesifikasi Standar Versi 2)

Harap diperhatikan bahwa arsitektur Sistem PEMALI versi 2 dibangun berlandaskan pada **Pydantic Core** dan manajemen dependensi **Directed Acyclic Graph (DAG)**. Dalam paradigma terbaru ini, modul berfungsi murni sebagai instrumen pengumpul data mentah. Semua bentuk pertimbangan etis terkait pedoman Tri Hita Karana, beserta pengambilan kesimpulan akhir, telah didelegasikan sepenuhnya kepada Cognitive Layer dari Large Language Model (LLM).

## Empat Regulasi Absolut Eksekusi Modul

1. **Skema Pydantic**: Setiap input data yang diinisiasi oleh AI wajib divalidasi menggunakan instance `BaseModel` dari Pydantic.
2. **Ketentuan Respons Absolut**: Fungsi `execute` mutlak menghasilkan objek `ModuleOutput` (yang mencakup atribut `status`, `data`, dan `error_msg`). Atribut lama seperti `agent_hint` dan `thk_alignment` telah dihapus dari protokol.
3. **Rantai Dependensi DAG**: Parameter `depends_on` wajib digunakan jika eksekusi suatu modul membutuhkan penyelesaian modul lain sebelumnya.
4. **Injeksi Konteks Konkuren**: Parameter `context` wajib digunakan untuk mengakses variabel internal sistem (seperti *environment variables* dan `session_id`), sehingga tidak membebani agen AI.

## Kerangka Kerja Komputasi Standar

File Python (`.py`) untuk modul baru harus ditempatkan di dalam direktori `/modules/` dan wajib mengikuti struktur standar berikut:

```python
from typing import Any, Dict
from pydantic import BaseModel, Field
from core.base_module import PemaliModuleV2, ModuleOutput

# 1. Penetapan Skema Masukan Berbasis Pydantic
class NamaModulInput(BaseModel):
    lokasi: str = Field(..., description="Nama lokasi spesifik yang ditargetkan untuk inspeksi.")
    # Tambahkan parameter lain sesuai kebutuhan dengan tipe data yang ketat

# 2. Deklarasi Kelas Entitas Modul
class TemplateModulBaru(PemaliModuleV2):
    # Deklarasi Metadata Modul
    name = "nama_modul_unik"  # WAJIB: Gunakan format snake_case.
    description = "Penjelasan komprehensif mengenai fungsi dan kapan AI harus menggunakan modul ini."
    input_schema = NamaModulInput
    depends_on = []  # Daftar modul prasyarat. Contoh: ["satellite_mod"]

    async def execute(self, params: NamaModulInput, context: Dict[str, Any]) -> ModuleOutput:
        """Logika Operasional Utama Modul"""
        try:
            # 1. Ekstraksi parameter input dari agen dan variabel sistem internal
            lokasi = params.lokasi
            session_id = context.get("session_id", "unknown")
            
            # 2. IMPLEMENTASI LOGIKA KOMPUTASI
            # (Contoh: pemanggilan API, query database, atau web scraping)
            hasil_mentah = {
                "lokasi": lokasi,
                "indikator": 85.5
            }
            
            # 3. Pengembalian data mentah murni tanpa analisis tambahan
            return ModuleOutput(
                status=200, 
                data=hasil_mentah
            )
            
        except Exception as e:
            # 4. Manajemen error; evaluasi pemulihan akan ditangani oleh Cognitive Layer
            return ModuleOutput(
                status=500, 
                error_msg=str(e)
            )
```

## Penjelasan Komponen Arsitektur Versi 2

- **`input_schema`**: Berfungsi sebagai mekanisme validasi otonom. Jika terdapat ketidaksesuaian tipe data pada input dari AI (misalnya, mengirim *integer* saat sistem meminta *string*), sistem akan otomatis menolak permintaan sebelum fungsi `execute` dijalankan.
- **`depends_on`**: Berupa array string. Jika modul membutuhkan data dari modul lain (misal: data satelit), deklarasikan sebagai `["satellite_mod"]`. Eksekusi modul ini akan ditahan hingga modul prasyarat selesai dengan status 200.
- **`ModuleOutput`**:
  - **`status`**: Menggunakan standar kode status HTTP (200 untuk sukses, 400 untuk error pada input, dan 500 untuk kegagalan internal sistem).
  - **`data`**: Payload teknis murni yang akan dikirimkan langsung ke *context window* LLM.
  - **`error_msg`**: Pesan error eksplisit untuk memfasilitasi proses pemulihan (Self-Correction Layer) oleh AI.