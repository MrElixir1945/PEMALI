"use client";

import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";
import {
  Satellite, Search, FileText,
  ScrollText, TreePine, Users,
} from "lucide-react";
import { motion } from "framer-motion";

export default function MethodologyPage() {
  const steps = [
    {
      icon: Satellite,
      iconColor: "#4A5E4A",
      iconBg: "#E8EDE8",
      title: "1. Pengumpulan Data dari Berbagai Sumber",
      detail: "PEMALI mengumpulkan data dari satelit NASA (NASA FIRMS untuk mendeteksi titik panas), sensor kualitas udara, data cuaca BMKG, serta berita dan media sosial. Seluruh data diverifikasi silang untuk memastikan akurasi.",
      image: "/images/methodology/pengumpulan-data.png",
    },
    {
      icon: Search,
      iconColor: "#4A5670",
      iconBg: "#E8ECF0",
      title: "2. Analisis oleh Agen Kecerdasan Buatan",
      detail: "Manager Agent memecah tugas audit ke beberapa sub-agent yang bekerja secara paralel: geo_agent memeriksa data satelit, water_agent menganalisis kualitas air, fire_agent mendeteksi titik panas, osint_agent memindai berita dan media sosial, serta scheduler_agent mengelola siklus otonom. Kelima sub-agent mengoperasikan 9 modul sensor sesuai keahlian masing-masing.",
      image: "/images/methodology/analisis oleh agen.png",
    },
    {
      icon: FileText,
      iconColor: "#6B4A3A",
      iconBg: "#F0ECE8",
      title: "3. Validasi dan Koreksi Otomatis",
      detail: "Apabila ditemukan data yang mencurigakan atau alat mengalami kegagalan, sistem akan melakukan percobaan ulang hingga tiga kali. Jika tetap gagal, Manager Agent akan mengirim agen lain untuk melakukan verifikasi silang sebelum data disatukan.",
      image: "/images/methodology/validasi-dan-koreksi.png",
    },
    {
      icon: FileText,
      iconColor: "#5A4A6B",
      iconBg: "#EEEDF0",
      title: "4. Penyusunan Laporan Akhir",
      detail: "Seluruh temuan ditulis dalam laporan berbahasa Indonesia yang naratif dan mudah dipahami. Laporan disimpan di database dan juga diubah menjadi vector embedding agar dapat ditanyakan kembali di kemudian hari melalui fitur tanya jawab pada laporan.",
      image: "/images/methodology/penyusunan laporan akhir.png",
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
              Mereka memiliki satelit, sensor, and akses terhadap berita — seluruhnya dikelola oleh
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
                  className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 mt-0.5 overflow-hidden"
                  style={{ backgroundColor: step.iconBg }}
                >
                  {step.image ? (
                    <img src={step.image} alt={step.title} className="w-full h-full object-cover" />
                  ) : (
                    <step.icon size={26} style={{ color: step.iconColor }} strokeWidth={1.5} />
                  )}
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
                  image: "/images/methodology/parahyangan .png",
                },
                {
                  icon: Users, color: "#4A5670", bg: "#E8ECF0",
                  title: "Pawongan",
                  sub: "Hubungan dengan Sesama",
                  desc: "Seluruh data audit bersifat transparan dan dapat diakses oleh masyarakat. Warga desa adat berhak mengetahui kondisi lingkungan di wilayahnya masing-masing.",
                  image: "/images/methodology/pawongan .png",
                },
                {
                  icon: ScrollText, color: "#6B4A3A", bg: "#F0ECE8",
                  title: "Palemahan",
                  sub: "Hubungan dengan Alam",
                  desc: "Pemantauan berkelanjutan terhadap hutan mangrove, subak, sungai, dan pantai. Deteksi dini memungkinkan pencegahan kerusakan lingkungan sebelum meluas.",
                  image: "/images/methodology/palemahan.png",
                },
              ].map((item) => (
                <div
                  key={item.title}
                  className="bg-white border-[0.5px] border-[var(--pemali-border)] rounded-xl p-5"
                >
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center mb-4 overflow-hidden"
                    style={{ backgroundColor: item.bg }}
                  >
                    {item.image ? (
                      <img src={item.image} alt={item.title} className="w-full h-full object-cover" />
                    ) : (
                      <item.icon size={22} style={{ color: item.color }} strokeWidth={1.5} />
                    )}
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
