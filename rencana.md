# 🗺️ Rencana Pengembangan Lanjutan PEMALI (Roadmap)

Saat ini, prototipe PEMALI berjalan dengan sangat baik secara lokal menggunakan **Mock Data** (data simulasi). Ini sudah sangat cukup untuk keperluan _demo lomba/presentasi_ karena menunjukkan fungsionalitas sistem secara sempurna tanpa adanya _delay_ dari _external API_.

Namun, untuk mengembangkan prototipe ini menjadi MVP (Minimum Viable Product) yang benar-benar siap beroperasi secara nyata, berikut adalah _roadmap_ pengembangan selanjutnya yang bisa Anda ikuti:

---

## 🟡 Fase 1: Transisi ke Data Nyata (Real API Integration)
_Fokus: Mengganti mock data di backend dengan koneksi ke sumber data riil._

* **Modul 1 (Satelit):**
  * Buat Service Account Google Cloud dan aktifkan **Google Earth Engine (GEE) API**.
  * Ubah `satellite_agent.py` untuk menarik nilai _Normalized Difference Vegetation Index_ (NDVI) menggunakan citra satelit Sentinel-2 / Landsat 8.
* **Modul 2 (OSINT):**
  * Daftarkan aplikasi di Twitter Developer Portal untuk mendapatkan Bearer Token, lalu integrasikan `tweepy` di `osint_agent.py`.
  * Integrasikan **HuggingFace API** untuk menjalankan model sentimen `IndoBERT` secara otomatis saat _tweet_ baru masuk.
* **Modul 4 (Kebijakan):**
  * Tulis parameter _Tri Hita Karana_ (THK) dan Awig-Awig desa ke dalam format JSON yang bisa diperbarui secara dinamis (tidak di-hardcode).

## 🟠 Fase 2: Implementasi LLM Orchestrator (Brain Layer)
_Fokus: Membuat "otak" PEMALI menjadi benar-benar agentic._

* **Transisi ke LangChain / CrewAI:** 
  * Saat ini `orchestrator.py` berjalan secara prosedural (langkah 1 -> 2 -> 3). Ubah ini menggunakan `LangChain` atau `CrewAI`.
  * **Goal:** Biarkan AI yang mengambil keputusan. Misalnya, jika data Twitter tidak cukup untuk mengukur _awareness_, agen AI dapat memutuskan sendiri untuk mengecek YouTube tanpa harus diprogram secara eksplisit.
* **Natural Language Generation (NLG):**
  * Gunakan OpenAI / Gemini API untuk menulis narasi "Justifikasi" dan "Rekomendasi Tindakan" ke Desa Adat agar bahasanya lebih mengalir, manusiawi, dan menyesuaikan konteks wilayah spesifik.

## 🔵 Fase 3: Persistensi Data (Database Setup)
_Fokus: Menyimpan riwayat audit untuk melihat tren jangka panjang._

* **Setup PostgreSQL / SQLite:**
  * Implementasikan ORM seperti `SQLAlchemy` atau `Prisma` di FastAPI.
  * Simpan hasil audit per wilayah ke database setiap kali pengecekan selesai.
* **Historical Tracking:**
  * Grafik "Tren NDVI 6 Bulan" di Frontend (Next.js) tidak lagi menggunakan mock data, melainkan mengambil riwayat audit bulan-bulan sebelumnya dari database.

## 🟢 Fase 4: Deployment & Production (Go-Live)
_Fokus: Membuat aplikasi bisa diakses siapa saja di internet._

* **Containerization:** Bungkus backend FastAPI dengan `Docker` agar mudah di-deploy di berbagai server tanpa konflik dependency.
* **Backend Hosting:** Deploy API ke **Render** atau **Railway**.
* **Frontend Hosting:** Deploy aplikasi Next.js ke **Vercel** (gratis dan sangat cepat).
* **Automated Cron Jobs:** Atur agar orkestrator berjalan secara otomatis (misal: sebulan sekali setiap tanggal 1) untuk meng-audit wilayah-wilayah prioritas di Bali tanpa harus dipicu manual.

---

### 💡 Saran Eksekusi Jangka Pendek
Jika target utama saat ini adalah **menang lomba**, saya sarankan **jangan buru-buru masuk ke Fase 1 atau 2 dulu**. Fokuslah berlatih presentasi menggunakan prototipe yang sudah ada, karena prototipe ini sudah membuktikan _"Proof of Concept"_ dari arsitektur yang Anda tawarkan di esai. Pindah ke data riil bisa memunculkan _rate-limit errors_ atau _timeout_ saat demo langsung!
