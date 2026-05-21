# Panduan Menjalankan Sistem PEMALI (Next.js Edition)

Dokumen ini berisi panduan langkah demi langkah untuk menjalankan ekosistem PEMALI AI Agentik di lokal Anda. Sistem PEMALI menggunakan arsitektur modern dengan **FastAPI sebagai Backend** dan **Next.js sebagai Frontend**.

## Prasyarat

Pastikan Anda memiliki hal-hal berikut terinstal:
- **Python 3.10+**
- **Node.js 18+**
- **Docker** & **Docker Compose**

---

## Langkah Persiapan (Satu Kali)

1.  **Konfigurasi Environment**:
    Salin file contoh env dan isi API Key Anda (khususnya `OPENROUTER_KEY`).
    ```bash
    cp .env.example .env
    ```

2.  **Setup Virtual Environment & Install Library**:
    ```bash
    # Buat venv jika belum ada
    python -m venv venv
    # Aktifkan venv
    source venv/bin/activate
    # Install dependensi
    pip install -r requirements.txt
    ```

3.  **Nyalakan Database (PostgreSQL)**:
    Gunakan Docker Compose untuk menjalankan database di background.
    ```bash
    docker compose up -d
    ```

4.  **Install Dependensi Frontend**:
    ```bash
    cd frontend
    npm install
    cd ..
    ```

---

## Urutan Eksekusi

Buka 3 tab/jendela terminal dan jalankan perintah berikut secara berurutan:

### Terminal 1: Backend (FastAPI)
Ini adalah server pusat yang menyediakan API bagi Agent dan Frontend.
```bash
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: Worker Node (Background Task)
Worker bertugas mengeksekusi tugas-tugas otonom (scheduling) yang direncanakan oleh Agent.
```bash
source venv/bin/activate
python worker.py
```

### Terminal 3: Frontend (Next.js)
Antarmuka utama "Lontar Digital" untuk audit.
```bash
cd frontend
npm run dev
```
*Akses di: **http://localhost:3000***

---

## Cara Melakukan Audit (Demo)

1. Buka browser di `http://localhost:3000`.
2. Klik tombol **"Enter Dashboard"**.
3. Di kolom instruksi, ketik perintah audit, contoh:
   - *"Audit kondisi lahan di Ubud dan kroscek legalitas areanya."*
   - *"Lakukan inspeksi di Gianyar."*
4. Klik **Kirim**.
5. Anda akan melihat AI mulai "berpikir" (Reasoning), memanggil alat satelit, dan menampilkan laporan final secara otomatis.

---

## Troubleshooting
- **ModuleNotFoundError: No module named 'dotenv'?** Pastikan Anda sudah menjalankan `pip install -r requirements.txt` di dalam virtual environment yang aktif.
- **Frontend tidak bisa connect ke Backend?** Pastikan Terminal 1 (FastAPI) berjalan di port 8000.
- **Database error?** Pastikan container Docker `pemali_db` sudah berjalan (`docker ps`).
