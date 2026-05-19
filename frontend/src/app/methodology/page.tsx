"use client";

import { useState } from "react";
import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";
import {
  Satellite, Search, FileText,
  ScrollText, TreePine, Users,
  ChevronDown, ChevronUp,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function MethodologyPage() {
  const [showTechnical, setShowTechnical] = useState(false);

  const steps = [
    {
      icon: Satellite,
      iconColor: "#4A5E4A",
      iconBg: "#E8EDE8",
      title: "1. Pengumpulan Data dari Berbagai Sumber",
      detail: "PEMALI mengumpulkan data dari satelit NASA (NASA FIRMS untuk mendeteksi titik panas), sensor kualitas udara, data cuaca BMKG, serta berita dan media sosial. Seluruh data diverifikasi silang untuk memastikan akurasi.",
    },
    {
      icon: Search,
      iconColor: "#4A5670",
      iconBg: "#E8ECF0",
      title: "2. Analisis oleh Agen Kecerdasan Buatan",
      detail: "Manager Agent memecah tugas audit ke beberapa sub-agent yang bekerja secara paralel: geo_agent memeriksa data satelit, water_agent menganalisis kualitas air, fire_agent mendeteksi titik panas, dan osint_agent memindai berita serta media sosial. Setiap agen memiliki keahlian spesifik sesuai bidangnya.",
    },
    {
      icon: FileText,
      iconColor: "#6B4A3A",
      iconBg: "#F0ECE8",
      title: "3. Validasi dan Koreksi Otomatis",
      detail: "Apabila ditemukan data yang mencurigakan atau alat mengalami kegagalan, sistem akan melakukan percobaan ulang hingga tiga kali. Jika tetap gagal, Manager Agent akan mengirim agen lain untuk melakukan verifikasi silang sebelum data disatukan.",
    },
    {
      icon: FileText,
      iconColor: "#5A4A6B",
      iconBg: "#EEEDF0",
      title: "4. Penyusunan Laporan Akhir",
      detail: "Seluruh temuan ditulis dalam laporan berbahasa Indonesia yang naratif dan mudah dipahami. Laporan disimpan di database dan juga diubah menjadi vector embedding agar dapat ditanyakan kembali di kemudian hari melalui fitur tanya jawab pada laporan.",
    },
  ];

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
              Methodology
            </div>
            <h1 className="font-serif text-[40px] font-light tracking-tight text-[var(--pemali-text-primary)] leading-[1.15] mb-4">
              Bagaimana Cara Kerja PEMALI?
            </h1>
            <p className="text-[14px] text-[var(--pemali-text-secondary)] leading-relaxed max-w-2xl">
              PEMALI dapat diibaratkan sebagai tim detektif lingkungan yang bekerja selama 24 jam penuh.
              Mereka memiliki satelit, sensor, dan akses terhadap berita — seluruhnya dikelola oleh
              kecerdasan buatan yang bertindak sebagai koordinator.
            </p>
          </motion.div>

          {/* Steps */}
          <div className="flex flex-col gap-4 mb-16">
            {steps.map((step, i) => (
              <motion.div
                key={step.title}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
                className="bg-white border-[0.5px] border-[var(--pemali-border)] rounded-xl p-6 flex items-start gap-5"
              >
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-0.5"
                  style={{ backgroundColor: step.iconBg }}
                >
                  <step.icon size={18} style={{ color: step.iconColor }} strokeWidth={1.5} />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-[14px] font-medium text-[var(--pemali-text-primary)] mb-1.5">
                    {step.title}
                  </h3>
                  <p className="text-[12px] text-[var(--pemali-text-secondary)] leading-relaxed">
                    {step.detail}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Technical Deep Dive */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.35 }}
            className="bg-white border-[0.5px] border-[var(--pemali-border)] rounded-xl p-6 mb-16"
          >
            <button
              onClick={() => setShowTechnical(!showTechnical)}
              className="w-full flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: "#F1EFE8" }}>
                  <Satellite size={15} className="text-[#5F5E5A]" strokeWidth={1.5} />
                </div>
                <span className="text-[11px] font-mono uppercase tracking-[0.08em] font-medium" style={{ color: "#888780" }}>
                  Penjelasan Teknis
                </span>
              </div>
              <div className="w-7 h-7 rounded-full flex items-center justify-center" style={{ backgroundColor: "#F1EFE8" }}>
                {showTechnical ? <ChevronUp size={14} className="text-[#5F5E5A]" /> : <ChevronDown size={14} className="text-[#5F5E5A]" />}
              </div>
            </button>

            <AnimatePresence>
              {showTechnical && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <div className="pt-6 mt-4 border-t border-[var(--pemali-border)]">
                    <div className="text-[12px] leading-relaxed" style={{ color: "var(--pemali-text-secondary)" }}>
                      <h4 className="text-[13px] font-medium text-[var(--pemali-text-primary)] mb-2">Arsitektur Sistem</h4>
                      <p className="mb-3">
                        PEMALI memiliki tiga lapisan utama. Pertama, <strong>Manager Agent</strong> — seperti project manager yang menerima perintah pengguna, menyusun strategi pelaksanaan audit, dan mendistribusikan tugas ke sub-agent.
                      </p>
                      <p className="mb-3">
                        Kedua, <strong>Sub-Agent</strong> — tim spesialis. Terdapat agen yang ahli membaca data satelit (geo_agent), agen yang memeriksa polusi air (water_agent), agen yang mendeteksi sumber api dari data termal (fire_agent), dan agen yang mencari informasi dari berita serta media sosial (osint_agent). Mereka dapat bekerja secara bersamaan atau berurutan tergantung kebutuhan.
                      </p>
                      <p className="mb-3">
                        Ketiga, <strong>Modul Sensor</strong> — perangkat yang digunakan. Modul seperti <em>weather_hazard_monitor</em> atau <em>fire_hotspot_detector</em> merupakan fungsi yang mengambil data langsung dari API eksternal (NASA, BMKG, dan lain-lain). Setiap modul hanya menjalankan satu tugas spesifik dan mengembalikan data mentah.
                      </p>
                      <p>
                        Seluruh proses ini dapat diamati secara langsung di halaman Dashboard — mulai dari Manager Agent berpikir, sub-agent bekerja, hingga laporan dihasilkan. Semua berjalan secara real-time dengan animasi sehingga pengguna mengetahui secara persis apa yang sedang terjadi.
                      </p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          {/* THK Section */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.4 }}
          >
            <div className="flex items-center gap-2 mb-5">
              <span className="text-[11px] font-mono uppercase tracking-[0.1em]" style={{ color: "#888780" }}>
                Selaras dengan Filosofi Tri Hita Karana
              </span>
            </div>
            <p className="text-[12px] text-[var(--pemali-text-secondary)] leading-relaxed mb-6">
              PEMALI tidak hanya mengejar data teknis. Setiap laporan audit senantiasa mempertimbangkan tiga keseimbangan kehidupan masyarakat Bali:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                {
                  icon: TreePine, color: "#4A5E4A", bg: "#E8EDE8",
                  title: "Parahyangan",
                  sub: "Hubungan dengan Tuhan",
                  desc: "Menjaga situs suci dan pura dari pembangunan ilegal. Satelit memantau kawasan sekitar pura agar tidak terjadi pelanggaran tata ruang.",
                },
                {
                  icon: Users, color: "#4A5670", bg: "#E8ECF0",
                  title: "Pawongan",
                  sub: "Hubungan dengan Sesama",
                  desc: "Seluruh data audit bersifat transparan dan dapat diakses oleh masyarakat. Warga desa adat berhak mengetahui kondisi lingkungan di wilayahnya masing-masing.",
                },
                {
                  icon: ScrollText, color: "#6B4A3A", bg: "#F0ECE8",
                  title: "Palemahan",
                  sub: "Hubungan dengan Alam",
                  desc: "Pemantauan berkelanjutan terhadap hutan mangrove, subak, sungai, dan pantai. Deteksi dini memungkinkan pencegahan kerusakan lingkungan sebelum meluas.",
                },
              ].map((item) => (
                <div
                  key={item.title}
                  className="bg-white border-[0.5px] border-[var(--pemali-border)] rounded-xl p-5"
                >
                  <div
                    className="w-9 h-9 rounded-lg flex items-center justify-center mb-4"
                    style={{ backgroundColor: item.bg }}
                  >
                    <item.icon size={16} style={{ color: item.color }} strokeWidth={1.5} />
                  </div>
                  <div className="text-[10px] font-mono tracking-wider mb-0.5" style={{ color: "#B4B2A9" }}>
                    {item.sub}
                  </div>
                  <h4 className="text-[13px] font-medium text-[var(--pemali-text-primary)] mb-2">
                    {item.title}
                  </h4>
                  <p className="text-[11px] text-[var(--pemali-text-secondary)] leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </main>
      <Footer />
    </>
  );
}
