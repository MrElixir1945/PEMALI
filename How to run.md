# Panduan Menjalankan Sistem PEMALI

Dokumen ini berisi panduan langkah demi langkah untuk menjalankan ekosistem PEMALI AI Agentik di lokal Anda. Sistem PEMALI terdiri dari beberapa komponen yang saling bekerja sama, sehingga harus dijalankan di terminal yang terpisah.

## Prasyarat
Sebelum menjalankan komponen apa pun, pastikan **Docker** sudah menyala di PC Anda, karena database PostgreSQL PEMALI (`pemali_db`) berjalan di dalam kontainer.

1. **Nyalakan Docker Desktop** (atau daemon Docker Anda).
2. Aktifkan *virtual environment* Python (jika Anda menggunakannya):
   ```bash
   source venv/bin/activate
   ```

---

## Urutan Eksekusi

Sistem ini membutuhkan beberapa terminal terpisah. Buka 4 tab/jendela terminal dan jalankan perintah berikut secara berurutan:

### Terminal 1: Communicate Layer (FastAPI)
Ini adalah server pusat yang menyediakan akses *Tool Calling* bagi AI Agent.
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
*(Biarkan terminal ini tetap menyala)*

### Terminal 2: Worker Node (Background Task)
Worker bertugas mengeksekusi *Autonomous Task* yang dijadwalkan oleh Agent (seperti pemantauan ulang otomatis).
```bash
python worker.py
```
*(Biarkan terminal ini tetap menyala)*

### Terminal 3: Dashboard Command Center
Dashboard interaktif berbasis CLI untuk memantau log reasoning AI Agent, status task, dan hasil audit.
```bash
python dashboard.py
```
*(Biarkan terminal ini tetap menyala untuk monitoring)*

### Terminal 4: Trigger Audit (Manual Testing)
Terminal ini digunakan untuk memicu agen memulai proses audit dan inspeksi awal melalui prompt yang sudah disiapkan.
```bash
python test_agent.py
```

---

## Alur Kerja (Workflow)
Saat Anda menjalankan `test_agent.py`, berikut adalah apa yang akan terjadi secara sistematis:
1. Orchestrator akan membaca instruksi dan meminta daftar alat (*tools*) dari FastAPI (`Terminal 1`).
2. Agen akan memanggil alat-alat (seperti satelit, verifikasi legalitas, dan analitik) dan mengirim hasilnya.
3. Agen menyimpan laporan akhir ke Database (PostgreSQL di Docker).
4. Agen menjadwalkan pemeriksaan ulang.
5. Anda dapat melihat proses reasoning ini secara *real-time* di Dashboard (`Terminal 3`).
6. Setelah waktu penjadwalan tiba, Worker (`Terminal 2`) akan kembali mengaktifkan agen secara otomatis untuk mengeksekusi pemeriksaan ulang.
