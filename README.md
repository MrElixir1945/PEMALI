# PEMALI (Pemeriksa Lingkungan Mandiri)

PEMALI adalah platform audit lingkungan otonom berbasis AI Agent yang dirancang untuk memantau kelestarian ekosistem di Bali berdasarkan filosofi **Tri Hita Karana**.

Sistem ini menggunakan arsitektur **Connector V2 (UTI Standard)** yang memungkinkan AI untuk secara mandiri memanggil berbagai modul audit (Satelit, OSINT, Komunitas) dan mengambil keputusan otonom.

## Fitur Utama
- **Autonomous Audit**: Agent mampu melakukan investigasi mandiri tanpa input manusia konstan.
- **Sentinel-2 Satellite Analysis**: Deteksi alih fungsi lahan dan kesehatan vegetasi (NDVI).
- **OSINT Intelligence**: Agregasi berita dan sentimen publik terkait isu lingkungan.
- **THK Alignment**: Setiap temuan dikategorikan ke dalam pilar Parahyangan, Pawongan, atau Palemahan.
- **Self-Scheduling**: Agent bisa menjadwalkan pemeriksaan ulang di masa depan.

## Arsitektur Sistem
Sistem dibagi menjadi tiga komponen utama:
1. **Communicate Layer (FastAPI)**: Menyediakan interface bagi AI untuk mengakses Tools (Modul).
2. **Orchestrator (The Brain)**: Logika penalaran ReAct menggunakan model Gemini 2.0 / Deepseek.
3. **Autonomous Worker**: Background service untuk mengeksekusi tugas yang dijadwalkan.

## Instalasi

1. **Clone Repository**
   ```bash
   git clone https://github.com/MrElixir1945/PEMALI.git
   cd PEMALI
   ```

2. **Setup Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Run the Application**
   ```bash
   python main.py
   ```

## Kontribusi
PEMALI sekarang open source. Semua kontribusi welcome.
- Fork repo, bikin branch, submit PR.
- Pastiin commit pake format: `feat:` atau `fix:` atau `docs:`.

## Lisensi
MIT License - lihat file [LICENSE](LICENSE) untuk detail.
