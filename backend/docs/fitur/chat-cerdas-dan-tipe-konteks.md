# Fitur: Chat Cerdas & Konteks Otomatis

> **Status**: ✅ Selesai — Sprint 3 (Narrative + SDUI + Telemetry)
> **File terkait**: `page.tsx`, `main.py`, `orchestrator.py`, `ObservationZone.tsx`

---

## 1. Chat Mode vs Audit Mode

### Masalah
Sebelumnya, dashboard masuk ke **Audit Mode** (menampilkan alur kerja agent) setiap kali ada event dari Manager — bahkan untuk percakapan biasa seperti "halo" atau "perkenalkan diri". Ini bikin UI berantakan karena workflow yang tidak relevan tetap ditampilkan.

### Solusi
Frontend hanya masuk ke Audit Mode jika **Manager benar-benar membuat rencana audit** (`metadata.phase === "planning"`). Percakapan biasa tetap di **Chat Mode** (full-width chat, tanpa workflow).

**Perubahan di `frontend/src/app/dashboard/page.tsx`**:
```tsx
// SEBELUM (terlalu agresif — trigger di banyak kondisi):
if (
  (event.node_id && event.node_id !== "manager" && event.node_id !== "system") ||
  (event.node_id === "manager" && event.metadata?.phase === "planning")
) {
  setAuditMode(true);
}

// SESUDAH (hanya trigger kalau benar-benar ada rencana audit):
if (event.node_id === "manager" && event.metadata?.phase === "planning") {
  setAuditMode(true);
}
```

**Perubahan di `backend/core/orchestrator.py`**:
- Chat response (tanpa plan) → Manager emit DONE dengan `metadata.type = "chat_response"`
- Audit response (dengan plan) → Planning event tetap seperti biasa

### Alur
```
User: "halo bro"
  → Manager detect: ini percakapan biasa (GATE LOGIC)
  → Manager emit DONE + metadata.type = "chat_response"
  → Frontend: tetap di Chat Mode ✓

User: "Audit vegetasi Ubud"
  → Manager detect: ini permintaan audit
  → Manager buat plan, emit THINKING + phase = "planning"
  → Frontend: masuk Audit Mode, tampilkan workflow ✓
```

---

## 2. Auto-Generate Title Histori Chat

### Masalah
Sebelumnya title sesi cuma `prompt[:30]` (30 karakter pertama input user). Contoh: user ngetik "Audit lingkungan daerah Badung dan cari informasi..." → title jadi "Audit lingkungan daerah Badung...". Tidak kontekstual dan tidak informatif.

### Solusi
Title di-generate dari response AI secara otomatis:
- **Audit report**: pakai heading pertama (`# `) dari laporan → "Analisis Kualitas Udara di Badung"
- **Chat biasa**: pakai kalimat pertama dari response AI → "Halo! Ada yang bisa saya bantu?"
- **Fallback**: ke prompt user kalau response kosong

**Perubahan di `backend/main.py` — `execute_agent_safely`**:
```python
# Setelah orchestrator.run() selesai:
if isinstance(result, str) and len(result) > 10:
    # Simpan ke AgentMemory
    db.add(AgentMemory(session_id=session_id, role="assistant", content=result))
    
    # Generate title dari response AI
    sess = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if sess:
        sess.last_activity = datetime.datetime.now(datetime.timezone.utc)
        if result.startswith("# "):
            # Audit report → pakai heading pertama
            ai_title = result.split("\n")[0].replace("# ", "").strip()
            sess.title = ai_title[:50]
```

### Contoh Hasil
| User Input | Title Sebelum | Title Sesudah |
|---|---|---|
| "halo" | "halo" | "Halo! Ada yang bisa saya bantu?" |
| "Perkenalkan diri anda" | "Perkenalkan diri anda" | "Saya Manager Agent untuk audit lingkungan Bali" |
| "Audit daerah badung cari info polusi udara" | "Audit daerah badung cari info..." | "Audit Polusi Udara di Badung" |
| "Cek kualitas air Sungai Ayung" | "Cek kualitas air Sungai Ayung" | "Analisis Kualitas Air Sungai Ayung" |

---

## 3. Format Laporan yang Rapi

### Masalah
Laporan audit sebelumnya menggunakan `===` separator dan ALL CAPS yang berantakan. Contoh:
```
========================================
DAERAH UBUD, GIANYAR, BALI
========================================
Ringkasan Eksekutif
----------------------------------------
...
```

### Solusi
Tambah aturan formatting ke synthesis system prompt di orchestrator:
- Gunakan markdown heading proper (`#`, `##`, `###`)
- Jangan pakai `===` atau `---` sebagai separator
- Jangan ALL CAPS untuk heading
- Struktur tetap: Ringkasan Eksekutif → Temuan → Rekomendasi → Kesimpulan

**Perubahan di `backend/core/orchestrator.py` — `synth_system`**:
```python
synth_system = (
    "..."
    "# FORMAT LAPORAN (WAJIB)\n"
    "1. Gunakan markdown heading: # untuk judul utama, ## untuk section, ### untuk subsection\n"
    "2. JANGAN gunakan === atau --- sebagai separator section\n"
    "3. JANGAN gunakan ALL CAPS untuk heading\n"
    "4. Struktur: # Judul Laporan → ## Ringkasan Eksekutif → ## Temuan → ## Rekomendasi → ## Kesimpulan\n"
    "5. Gunakan bullet points dan numbered list untuk data\n"
    "6. Paragraf pendek (max 4 kalimat)\n"
    "..."
)
```

### Hasil yang Diharapkan
```markdown
# Analisis Kualitas Udara di Badung

## Ringkasan Eksekutif
Audit lingkungan di Kabupaten Badung menunjukkan...
```

---

## 4. Status Agent yang Realistis

### Masalah
Sebelumnya, agent yang tidak digunakan langsung di-SKIP saat spawning event diterima (berdasarkan `planned_agents`). Ini bikin user bingung karena agent seperti "Water Audit" langsung muncul "Dilewati" padahal proses masih berjalan.

### Solusi
SKIP hanya muncul **setelah synthesis selesai**. Selama proses berjalan:
- Agent aktif → tampilkan status sebenarnya (Memproses/Selesai)
- Agent tidak aktif → tetap "Menunggu" (tidak langsung "Dilewati")
- Setelah synthesis DONE → sisa agent yang masih "Menunggu" diubah jadi "Dilewati"

**Perubahan di `ObservationZone.tsx`** — hapus planned_agents SKIP detection dari spawning event, pertahankan SKIP hanya di synthesis DONE handler.

### Status Label Mapping
| Status Internal | Tampilan |
|---|---|
| `PENDING` | Menunggu |
| `EXECUTING` | Memproses |
| `DONE` | Selesai |
| `SKIP` | Dilewati |

---

## Ringkasan File yang Diubah

| File | Baris | Perubahan |
|---|---|---|
| `frontend/src/app/dashboard/page.tsx` | ~6 | Fix kondisi audit mode (hapus sub-agent check) |
| `backend/main.py` | ~15 | Title contextual dari response AI |
| `backend/core/orchestrator.py` | ~20 | Formatting rules synth prompt + metadata chat_response |
| `frontend/src/components/pemali/dashboard/ObservationZone.tsx` | ~20 | Hapus planned_agents SKIP detection |
