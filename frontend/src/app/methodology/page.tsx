"use client";

import { useState } from "react";
import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";
import { Eye, Brain, FileText, Shield, Scale, Heart, ChevronDown, ChevronUp } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function MethodologyPage() {
  const [showTechnical, setShowTechnical] = useState(false);

  return (
    <>
      <NavBar />
      <main className="flex-1 max-w-4xl mx-auto px-8 py-16 w-full">
        <div className="prose prose-stone max-w-none">
          <h1 className="font-serif text-5xl font-semibold mb-8">Cara Kerja Kami</h1>
          <p className="text-xl text-stone-600 font-light leading-relaxed mb-12">
            PEMALI bekerja seperti detektif digital. Ia tidak hanya melihat data, tapi 'berpikir' untuk menghubungkan temuan satelit dengan kondisi nyata di lapangan.
          </p>

          <div className="poleng-divider my-12"></div>

          <h2 className="font-serif text-3xl font-semibold mb-6 italic">Melihat, Berpikir, Melindungi.</h2>
          <p className="text-lg">
            Sistem kami dirancang agar setiap keputusan yang diambil memiliki alasan yang kuat dan dapat dipertanggungjawabkan.
          </p>
          
          <div className="grid grid-cols-1 gap-8 my-12">
            <div className="bg-white border border-stone-200 p-8 rounded-2xl shadow-sm">
              <div className="flex items-start gap-6">
                <div className="bg-stone-100 w-14 h-14 rounded-2xl flex items-center justify-center shrink-0">
                  <Eye className="w-7 h-7 text-stone-800" />
                </div>
                <div>
                  <h3 className="font-serif text-2xl font-semibold mb-2">1. Melihat dari Langit (Observasi)</h3>
                  <p className="text-stone-600 leading-relaxed mb-4">
                    PEMALI menggunakan mata satelit untuk memantau kesehatan hutan dan lahan di Bali secara langsung dari angkasa. Kami dapat melihat perubahan yang tidak terlihat oleh mata manusia biasa.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white border border-stone-200 p-8 rounded-2xl shadow-sm">
              <div className="flex items-start gap-6">
                <div className="bg-stone-100 w-14 h-14 rounded-2xl flex items-center justify-center shrink-0">
                  <Brain className="w-7 h-7 text-stone-800" />
                </div>
                <div>
                  <h3 className="font-serif text-2xl font-semibold mb-2">2. Menganalisis Masalah (Analisis)</h3>
                  <p className="text-stone-600 leading-relaxed mb-4">
                    AI akan membandingkan apa yang ia lihat dengan aturan yang berlaku untuk memastikan tidak ada pelanggaran alam. Ia 'menghubungkan titik-titik' data untuk menemukan anomali.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white border border-stone-200 p-8 rounded-2xl shadow-sm">
              <div className="flex items-start gap-6">
                <div className="bg-stone-100 w-14 h-14 rounded-2xl flex items-center justify-center shrink-0">
                  <FileText className="w-7 h-7 text-stone-800" />
                </div>
                <div>
                  <h3 className="font-serif text-2xl font-semibold mb-2">3. Memberikan Laporan (Aksi)</h3>
                  <p className="text-stone-600 leading-relaxed mb-4">
                    Setelah yakin, sistem akan otomatis membuat rangkuman audit yang siap digunakan oleh pihak berwenang. Tidak ada data yang terlewatkan.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Progressive Disclosure for Technical Details */}
          <div className="bg-stone-50 rounded-2xl p-8 mb-16 border border-stone-100">
            <button 
              onClick={() => setShowTechnical(!showTechnical)}
              className="w-full flex items-center justify-between text-stone-500 hover:text-stone-900 transition-colors"
            >
              <span className="text-xs font-semibold uppercase tracking-widest">Detail Teknis (ReAct & Sentinel-2)</span>
              {showTechnical ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            
            <AnimatePresence>
              {showTechnical && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <div className="pt-8 text-sm text-stone-600 leading-relaxed border-t border-stone-200 mt-6">
                    Sistem berbasis <strong>ReAct (Reasoning & Acting)</strong>. Setiap audit melalui fase observasi spasial menggunakan integrasi citra satelit <strong>Sentinel-2</strong> untuk mendapatkan data <strong>NDVI</strong> (indeks kesehatan vegetasi) terkini. AI memvalidasi hipotesis kerusakan lingkungan berdasarkan observasi tersebut sebelum melakukan eksekusi manifest modul melalui Unified Tool Interface.
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <h2 className="font-serif text-3xl font-semibold mb-8 text-center">Menjaga Keseimbangan Tradisi</h2>
          <p className="text-center text-lg mb-12">Kami memastikan teknologi tidak merusak tradisi. Algoritma kami dirancang untuk menjaga keseimbangan sesuai nilai leluhur.</p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
            <div className="text-center">
              <div className="bg-stone-100 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4">
                <Heart className="w-6 h-6 text-red-800" />
              </div>
              <h4 className="font-serif text-lg font-semibold mb-2">Parahyangan</h4>
              <p className="text-xs text-stone-500">Menjaga kesucian area pura agar tetap terjaga dari pembangunan ilegal.</p>
            </div>
            <div className="text-center">
              <div className="bg-stone-100 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4">
                <Scale className="w-6 h-6 text-stone-800" />
              </div>
              <h4 className="font-serif text-lg font-semibold mb-2">Pawongan</h4>
              <p className="text-xs text-stone-500">Menjaga keharmonisan warga dengan memastikan keadilan tata ruang.</p>
            </div>
            <div className="text-center">
              <div className="bg-stone-100 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4">
                <Shield className="w-6 h-6 text-[#2F4F4F]" />
              </div>
              <h4 className="font-serif text-lg font-semibold mb-2">Palemahan</h4>
              <p className="text-xs text-stone-500">Menjaga kelestarian alam agar tetap hijau dan asri untuk masa depan.</p>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
