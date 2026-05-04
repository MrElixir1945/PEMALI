# PEMALI (Pemeriksa Lingkungan Mandiri)

PEMALI adalah platform audit lingkungan otonom berbasis AI Agent yang dirancang untuk memantau kelestarian ekosistem di Bali berdasarkan filosofi **Tri Hita Karana**. 

Sistem ini menggunakan arsitektur **Connector V2 (UTI Standard)** yang memungkinkan AI untuk secara mandiri memanggil berbagai modul audit (Satelit, OSINT, Komunitas) dan mengambil keputusan otonom.

## 🚀 Fitur Utama
- **Autonomous Audit**: Agent mampu melakukan investigasi mandiri tanpa input manusia konstan.
- **Sentinel-2 Satellite Analysis**: Deteksi alih fungsi lahan dan kesehatan vegetasi (NDVI).
- **OSINT Intelligence**: Agregasi berita dan sentimen publik terkait isu lingkungan.
- **THK Alignment**: Setiap temuan dikategorikan ke dalam pilar Parahyangan, Pawongan, atau Palemahan.
- **Self-Scheduling**: Agent bisa menjadwalkan pemeriksaan ulang di masa depan.

## 🛠 Arsitektur Sistem
Sistem dibagi menjadi tiga komponen utama:
1. **Communicate Layer (FastAPI)**: Menyediakan interface bagi AI untuk mengakses "Tools" (Modul).
2. **Orchestrator (The Brain)**: Logika penalaran ReAct menggunakan model Gemini 2.0 / Deepseek.
3. **Autonomous Worker**: Background service untuk mengeksekusi tugas yang dijadwalkan.

## 📦 Instalasi

1. **Clone Repository**
   ```bash
   git clone <repo-url>
   cd PEMALI
   ```

2. **Setup Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

3. **Database Configuration**
   Pastikan PostgreSQL berjalan dan edit `core/database.py` untuk kredensial. Inisialisasi tabel dengan:
   ```bash
   python3 -c "from core.database import init_db; init_db()"
   ```

## 🚦 Cara Menjalankan

Buka 3 terminal terpisah:

- **Terminal 1 (API Server)**:
  `./venv/bin/python main.py`
- **Terminal 2 (Worker)**:
  `./venv/bin/python worker.py`
- **Terminal 3 (Dashboard)**:
  `./venv/bin/python dashboard.py`

Untuk memulai audit manual pertama kali:
```bash
./venv/bin/python test_agent.py
```

## 🧩 Pengembangan Modul Baru
PEMALI mendukung **Auto-Discovery**. Cukup buat file baru di folder `modules/` yang mewarisi class `PemaliModule`. Panduan lengkap ada di [MODULE_TEMPLATE.md](./MODULE_TEMPLATE.md).

---
**Digital Manuscript for Environmental Sovereignty.**
