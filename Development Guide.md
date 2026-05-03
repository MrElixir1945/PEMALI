# PEMALI Development Master Specification (V3.0)

## 1. Executive Summary & Philosophy
**Project Name:** PEMALI (Platform Ekologi Modular Agentic berbasis Artificial Intelligence).
**Context:** Festival Pelajar Ajeg Bali Ke-4 2026.
**Core Philosophy:** Mengadopsi nilai "Pemali" (pantangan adat) sebagai sistem peringatan dini digital yang menjaga keseimbangan alam Bali[cite: 1]. Sistem ini beroperasi berdasarkan filosofi **Tri Hita Karana (THK)** untuk memastikan teknologi selaras dengan kearifan lokal[cite: 1].

## 2. Strategic Objectives & Standardization Goals
Proyek ini dikembangkan dengan tujuan utama yang menjadi standar bagi seluruh modul:
*   **Otonomi Penuh**: Sistem harus mampu berjalan sendiri untuk mendeteksi anomali lingkungan tanpa intervensi manual yang konstan[cite: 1].
*   **Standarisasi Modular (UTI)**: Menjamin setiap modul baru (internal atau komunitas) dapat terintegrasi secara instan (*plug-and-play*)[cite: 1].
*   **Efisiensi Audit**: Mengganti survei lapangan yang mahal dan lambat dengan audit berbasis data satelit dan media sosial[cite: 1].
*   **Transparansi & Akuntabilitas**: Setiap tindakan AI harus tercatat dalam *memory* dan dapat dijelaskan melalui kacamata kebijakan lokal[cite: 1].

## 3. Architecture Topology (Communicate Layer Model)
Berdasarkan standar sistem agentic, PEMALI menggunakan model **Decoupled Architecture**[cite: 1]:

*   **UI/Terminal Control**: Antarmuka kontrol bagi siswa/supervisor[cite: 1].
*   **Auth Layer**: Gerbang keamanan sebelum akses ke inti sistem[cite: 1].
*   **AI Agent (Reasoning Engine)**: Otak pusat yang menggunakan pola **ReAct (Reason + Act)** untuk memecahkan masalah[cite: 1].
*   **Tool Call Capability Support**: Komponen yang menerjemahkan niat AI menjadi *command* JSON yang valid[cite: 1].
*   **Communicate Layer (The Dispatcher)**: Jantung sistem yang mengelola lalu lintas JSON, memvalidasi input/output, dan menghubungkan AI ke modul-modul[cite: 1].
*   **Memory Store**: Tempat penyimpanan *state* aktif, histori audit, dan *vector database* untuk tanya-jawab[cite: 1].
*   **Execution Modules**: Unit kerja teknis (Satellite, OSINT, Priority, Policy) yang menjalankan tugas spesifik[cite: 1].

## 4. Unified Tool Interface (UTI) Standards
UTI adalah "kontrak" yang wajib diikuti oleh semua pengembang modul agar AI Agent dapat berinteraksi dengan benar[cite: 1].

### 4.1 Input Specification (The Manifest)
Setiap modul wajib mengekspos `manifest` dalam format JSON Schema yang berisi:
*   **`name`**: Identitas unik modul[cite: 1].
*   **`description`**: Penjelasan fungsi modul dalam bahasa manusia yang sangat detail agar AI tahu kapan harus menggunakannya[cite: 1].
*   **`parameters`**: Definisi tipe data (string, integer, etc.) dan keterangan setiap parameter[cite: 1].

### 4.2 Output Specification (ModuleResponse)
Semua modul wajib mengembalikan objek dengan struktur sebagai berikut:
*   **`status`**: "success" atau "error"[cite: 1].
*   **`data`**: Dictionary berisi data teknis mentah[cite: 1].
*   **`agent_hint`**: Penjelasan singkat dalam bahasa manusia agar AI Agent bisa langsung memahami hasil tanpa perlu memproses data mentah[cite: 1].
*   **`thk_alignment`**: Analisis kaitan hasil dengan pilar Parahyangan, Pawongan, atau Palemahan[cite: 1].

## 5. Memory Management System
Memory digunakan untuk memberikan konteks dan kesadaran pada AI Agent[cite: 1]:
*   **Short-term (Context)**: Menyimpan variabel dari langkah sebelumnya (misal: koordinat wilayah) agar modul selanjutnya bisa langsung bekerja[cite: 1].
*   **Long-term (Historical)**: Menyimpan database audit masa lalu untuk perbandingan tren kerusakan[cite: 1].
*   **Semantic (Vector)**: Menggunakan ChromaDB untuk menyimpan teks laporan agar pengguna bisa berinteraksi secara tanya-jawab dengan AI mengenai masalah tertentu[cite: 1].

## 6. Developer Workflow & SOP
Tim pengembang wajib mengikuti prosedur berikut:
1.  **Inheritance**: Gunakan `PemaliModule` sebagai basis kelas di Python[cite: 1].
2.  **Async Implementation**: Gunakan `async def execute` agar sistem tidak mengalami *blocking* saat menunggu data[cite: 1].
3.  **Sanitization**: Bersihkan semua input dari modul OSINT untuk mencegah serangan *code injection*[cite: 1].
4.  **Auto-Discovery**: Simpan file modul di folder `/modules/` agar sistem dapat mendeteksinya secara otomatis melalui `Registry`[cite: 1].

## 7. Autonomous Reasoning Loop
1.  **Trigger**: Perubahan data satelit atau jadwal rutin memicu agen[cite: 1].
2.  **Reasoning**: Agen menganalisis data awal dan menentukan alat (module) mana yang dibutuhkan[cite: 1].
3.  **Action**: Agen mengirim JSON *call* melalui Communicate Layer[cite: 1].
4.  **Observation**: Agen menerima hasil, memperbarui memori, dan memutuskan apakah audit selesai atau butuh modul tambahan[cite: 1].

## 8. Module Registry System (`registry.py`)
`registry.py` adalah komponen yang melakukan inspeksi otomatis pada direktori `/modules` untuk mendaftarkan semua modul yang valid ke dalam sistem. Tanpa komponen ini, sistem memerlukan manual import yang kaku; dengan adanya `registry.py`, sistem menjadi benar-benar *plug-and-play*.

**Penjelasan Mekanisme `registry.py`**:
*   **Auto-Discovery**: Skrip akan melakukan *scan* pada folder `/modules` dan mencari file berektensi `.py`.
*   **Dynamic Loading**: Menggunakan `importlib` untuk me-load modul ke dalam memori secara *on-the-fly*.
*   **Validation**: Memastikan kelas di dalam file tersebut adalah turunan dari `PemaliModule` (sesuai standar UTI).
*   **Centralized Catalog**: Menyediakan satu *source of truth* bagi AI Agent untuk melihat daftar manifest dari semua *tool* yang tersedia.

---
**Standard Authority**: PEMALI Core Engineering Team[cite: 1].
**Project Timeline**: 13-Day Hyper-Sprint[cite: 1].