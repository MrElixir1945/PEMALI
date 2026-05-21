"use client";

import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";
import CodeBlock from "@/components/CodeBlock";
import {
  GitBranch, Network, Cpu, FileJson,
  Zap, Layers, Workflow,
} from "lucide-react";
import { motion } from "framer-motion";

const telegramFlow = `# Data yang dikirim ke dashboard secara real-time
# Setiap kali agen berubah status, data berikut dikirim:

{
  "trace_id": "tr-abc123",
  "node_id": "geo_agent",
  "node_type": "SubAgent",
  "state": "THINKING",
  "narrative": "Saya akan memeriksa data vegetasi Ubud...",
  "timestamp": 1712345678
}

# Frontend cukup mendengarkan melalui EventSource:
# new EventSource("/api/telemetry")`;

const dagDiagram = `# Manager Agent menyusun rencana kerja seperti berikut:
# Tugas tanpa dependensi dijalankan BERSAMAAN (paralel)

geo_agent ──────────────┐
                        ├──→ synthesis (menunggu semua selesai)
osint_agent ────────────┘

# Apabila terdapat 3 tugas, 2 tugas pertama berjalan bersamaan,
# tugas ketiga menunggu 2 tugas sebelumnya`;                                

const manifestExample = `# Contoh "manifest" atau identitas modul
# Ini memberitahu sistem: "Fungsi apa yang saya miliki?"

{
  "name": "weather_hazard_monitor",
  "description": "Mengambil data cuaca ekstrem di suatu lokasi",
  "parameters": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "Nama lokasi di Bali"
      }
    },
    "required": ["location"]
  }
}`;

const stackItems = [
  {
    icon: Workflow,
    label: "Koordinator",
    value: "Manager Agent",
    desc: "Berfungsi seperti project manager. Manager Agent yang merencanakan, membagi tugas, dan memastikan seluruh sub-agent menyelesaikan pekerjaan tepat waktu.",
    image: "/images/engginering/manager agent.png",
  },
  {
    icon: Cpu,
    label: "Tim Spesialis",
    value: "Sub-Agent (×5)",
    desc: "Terdiri dari geo_agent (data satelit), water_agent (kualitas air), fire_agent (titik panas), osint_agent (berita & media sosial), dan scheduler_agent (siklus otonom). Masing-masing memiliki perangkat sensor tersendiri.",
    image: "/images/engginering/sub-agent.png",
  },
  {
    icon: Layers,
    label: "Perangkat Sensor",
    value: "Modul Sensor (9+)",
    desc: "9 modul aktif: weather_hazard_monitor, fire_hotspot_detector, air_quality_index, earthquake_risk_monitor, sea_level_tide_monitor, osint_web_search, osint_trend_scanner, osint_instagram_monitor, dan scheduler_mod. Tambah file Python baru, sistem auto-detect.",
    image: "/images/engginering/sensor.png",
  },
  {
    icon: Zap,
    label: "Siaran Langsung",
    value: "SSE Telemetry",
    desc: "Setiap langkah agen dikirim langsung ke dashboard. Pengguna dapat melihat proses berpikir agen secara real-time.",
    image: "/images/engginering/sse telementry.png",
  },
  {
    icon: GitBranch,
    label: "Alur Kerja",
    value: "DAG Orchestration",
    desc: "Tugas yang tidak saling terkait dikerjakan secara bersamaan. Tugas yang memerlukan data dari agen lain akan menunggu terlebih dahulu.",
    image: "/images/engginering/dag orchestration.png",
  },
  {
    icon: FileJson,
    label: "Penyimpanan",
    value: "PostgreSQL + ChromaDB",
    desc: "Data audit disimpan di database SQL. Vector embedding disimpan agar dapat ditanyakan kembali melalui fitur RAG (Retrieval-Augmented Generation).",
    image: "/images/engginering/database.png",
  },
];

export default function EngineeringPage() {
  return (
    <>
      <NavBar />
      <main
        className="flex-1 min-h-screen"
        style={{ backgroundColor: "var(--color-background-tertiary, #F0EFEA)" }}
      >
        <div className="max-w-4xl mx-auto px-6 lg:px-8 py-16">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
            className="mb-12"
          >
            <div className="text-[11px] font-mono uppercase tracking-[0.1em] mb-3" style={{ color: "#888780" }}>
              Engineering
            </div>
            <h1 className="font-serif text-[40px] font-light tracking-tight text-[var(--pemali-text-primary)] leading-[1.15] mb-4">
              Cara Kerja Sistem
            </h1>
            <p className="text-[14px] text-[var(--pemali-text-secondary)] leading-relaxed max-w-2xl">
              Secara sederhana, PEMALI dapat diibaratkan sebagai sebuah perusahaan kecil yang memiliki 
              seorang <strong>manager</strong>, beberapa <strong>tim spesialis</strong>, dan berbagai 
              <strong>perangkat</strong>. Seluruh aktivitas mereka dapat dipantau langsung dari dashboard.
            </p>
          </motion.div>

          {/* Komponen Utama — grid 3 kolom */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-16"
          >
            {stackItems.map((item, i) => (
              <div
                key={item.label}
                className="bg-white border-[0.5px] border-[var(--pemali-border)] rounded-xl p-5"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-12 h-12 rounded-xl flex items-center justify-center overflow-hidden" style={{ backgroundColor: "#F1EFE8" }}>
                    {item.image ? (
                      <img src={item.image} alt={item.label} className="w-full h-full object-cover" />
                    ) : (
                      <item.icon size={22} className="text-[#5F5E5A]" strokeWidth={1.5} />
                    )}
                  </div>
                  <span className="text-[10px] font-mono uppercase tracking-[0.08em] font-medium" style={{ color: "#B4B2A9" }}>
                    {item.label}
                  </span>
                </div>
                <div className="text-[13px] font-medium text-[var(--pemali-text-primary)] mb-1">
                  {item.value}
                </div>
                <p className="text-[11px] text-[var(--pemali-text-secondary)] leading-relaxed">
                  {item.desc}
                </p>
              </div>
            ))}
          </motion.div>

          {/* Alur Kerja DAG */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.15 }}
            className="bg-white border-[0.5px] border-[var(--pemali-border)] rounded-xl p-6 mb-6"
          >
            <div className="flex items-start gap-4 mb-4">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 overflow-hidden" style={{ backgroundColor: "#E8EDE8" }}>
                <img src="/images/engginering/dag orchestration.png" alt="DAG" className="w-full h-full object-cover" />
              </div>
              <div>
                <h2 className="text-[14px] font-medium text-[var(--pemali-text-primary)] mb-1">
                  Alur Kerja: DAG (Directed Acyclic Graph)
                </h2>
                <p className="text-[12px] text-[var(--pemali-text-secondary)] leading-relaxed">
                  Manager Agent menyusun rencana kerja dalam bentuk <strong>grafik tugas</strong>.
                  Sebagai ilustrasi, ketika memasak: sambil menunggu air mendidih, kita dapat memotong bawang.
                  Tidak perlu menunggu satu per satu. PEMALI bekerja dengan prinsip yang sama.
                </p>
              </div>
            </div>
            <CodeBlock code={dagDiagram} filename="Alur DAG — tugas independen berjalan paralel" />
          </motion.div>

          {/* Telemetry */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.2 }}
            className="bg-white border-[0.5px] border-[var(--pemali-border)] rounded-xl p-6 mb-6"
          >
            <div className="flex items-start gap-4 mb-4">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 overflow-hidden" style={{ backgroundColor: "#E8ECF0" }}>
                <img src="/images/engginering/sse telementry.png" alt="SSE Telemetry" className="w-full h-full object-cover" />
              </div>
              <div>
                <h2 className="text-[14px] font-medium text-[var(--pemali-text-primary)] mb-1">
                  Data Real-Time ke Dashboard
                </h2>
                <p className="text-[12px] text-[var(--pemali-text-secondary)] leading-relaxed">
                  Setiap kali agen berubah status (dari "berpikir" menjadi "bekerja" kemudian "selesai"),
                  data langsung dikirim ke dashboard menggunakan teknologi <strong>SSE (Server-Sent Events)</strong>.
                  Halaman tidak perlu di-refresh — semua informasi muncul secara otomatis.
                </p>
              </div>
            </div>
            <CodeBlock code={telegramFlow} filename="Contoh data yang dikirim ke dashboard" />
          </motion.div>

          {/* UTI */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.25 }}
            className="bg-white border-[0.5px] border-[var(--pemali-border)] rounded-xl p-6 mb-6"
          >
            <div className="flex items-start gap-4 mb-4">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 overflow-hidden" style={{ backgroundColor: "#EEEDF0" }}>
                <img src="/images/engginering/sensor.png" alt="Sensor" className="w-full h-full object-cover" />
              </div>
              <div>
                <h2 className="text-[14px] font-medium text-[var(--pemali-text-primary)] mb-1">
                  Modul: Perangkat Sensor
                </h2>
                <p className="text-[12px] text-[var(--pemali-text-secondary)] leading-relaxed">
                  Modul merupakan perangkat yang digunakan sub-agent untuk mengambil data sesungguhnya.
                  Contohnya <em>weather_hazard_monitor</em> untuk memeriksa cuaca, atau <em>fire_hotspot_detector</em>
                  untuk mendeteksi sumber api. Ingin menambahkan modul baru? Cukup membuat file Python,
                  sistem akan secara otomatis mendeteksi dan mendaftarkannya — tanpa perlu memodifikasi kode lainnya.
                </p>
              </div>
            </div>
            <CodeBlock code={manifestExample} filename="Contoh identitas modul" />
          </motion.div>

          {/* Footer */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.3 }}
            className="text-[11px] text-center mt-12 font-mono" style={{ color: "#B4B2A9" }}
          >
            PEMALI Core v2.6 — Stack: Next.js 15 · FastAPI · PostgreSQL · ChromaDB
          </motion.div>
        </div>
      </main>
      <Footer />
    </>
  );
}
