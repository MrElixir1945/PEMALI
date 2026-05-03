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
      <main className="flex-1 max-w-4xl mx-auto px-8 py-16 w-full text-stone-800">
        <div className="prose prose-stone max-w-none">
          <h1 className="font-serif text-5xl font-semibold mb-8 text-stone-900">Cara Kerja Kami</h1>
          <p className="text-xl text-stone-600 font-light leading-relaxed mb-12">
            PEMALI bekerja seperti detektif digital. Ia tidak hanya melihat data, tapi 'berpikir' untuk menghubungkan temuan satelit dengan kondisi nyata di lapangan.
          </p>

          <div className="poleng-divider my-12"></div>

          <h2 className="font-serif text-3xl font-semibold mb-6 italic text-stone-800">Melihat, Berpikir, Melindungi.</h2>
          <p className="text-lg text-stone-600 mb-12">
            Sistem kami dirancang agar setiap keputusan yang diambil memiliki alasan yang kuat dan dapat dipertanggungjawabkan.
          </p>
          
          <div className="grid grid-cols-1 gap-8 my-12">
            <div className="bg-white border border-stone-200 p-8 rounded-[2.5rem] shadow-sm">
              <div className="flex flex-col md:flex-row items-center md:items-start gap-8 text-center md:text-left">
                <div className="bg-stone-50 w-16 h-16 rounded-3xl flex items-center justify-center shrink-0 border border-stone-100">
                  <Eye className="w-8 h-8 text-stone-800" />
                </div>
                <div>
                  <h3 className="font-serif text-2xl font-semibold mb-3 text-stone-900">1. Melihat dari Langit</h3>
                  <p className="text-stone-600 leading-relaxed">
                    PEMALI menggunakan mata satelit untuk memantau kesehatan hutan dan lahan di Bali secara langsung dari angkasa. Kami dapat melihat perubahan yang tidak terlihat oleh mata manusia biasa.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white border border-stone-200 p-8 rounded-[2.5rem] shadow-sm">
              <div className="flex flex-col md:flex-row items-center md:items-start gap-8 text-center md:text-left">
                <div className="bg-stone-50 w-16 h-16 rounded-3xl flex items-center justify-center shrink-0 border border-stone-100">
                  <Brain className="w-8 h-8 text-stone-800" />
                </div>
                <div>
                  <h3 className="font-serif text-2xl font-semibold mb-3 text-stone-900">2. Menganalisis Masalah</h3>
                  <p className="text-stone-600 leading-relaxed">
                    AI akan membandingkan apa yang ia lihat dengan aturan yang berlaku untuk memastikan tidak ada pelanggaran alam. Ia 'menghubungkan titik-titik' data untuk menemukan anomali.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white border border-stone-200 p-8 rounded-[2.5rem] shadow-sm">
              <div className="flex flex-col md:flex-row items-center md:items-start gap-8 text-center md:text-left">
                <div className="bg-stone-50 w-16 h-16 rounded-3xl flex items-center justify-center shrink-0 border border-stone-100">
                  <FileText className="w-8 h-8 text-stone-800" />
                </div>
                <div>
                  <h3 className="font-serif text-2xl font-semibold mb-3 text-stone-900">3. Memberikan Laporan</h3>
                  <p className="text-stone-600 leading-relaxed">
                    Setelah yakin, sistem akan otomatis membuat rangkuman audit yang siap digunakan oleh pihak berwenang. Tidak ada data yang terlewatkan.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-stone-900 rounded-[2.5rem] p-10 mb-20 text-white shadow-xl shadow-stone-200">
            <button 
              onClick={() => setShowTechnical(!showTechnical)}
              className="w-full flex items-center justify-between text-white/50 hover:text-white transition-colors"
            >
              <span className="text-[10px] font-bold uppercase tracking-[0.2em]">Technical Deep Dive</span>
              <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center group-hover:bg-white/20">
                {showTechnical ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
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
                  <div className="pt-8 text-sm text-stone-300 leading-relaxed border-t border-white/10 mt-6 font-light">
                    Sistem berbasis <strong>ReAct (Reasoning & Acting)</strong>. Setiap audit melalui fase observasi spasial menggunakan integrasi citra satelit <strong>Sentinel-2</strong> untuk mendapatkan data <strong>NDVI</strong> (indeks kesehatan vegetasi) terkini. AI memvalidasi hipotesis kerusakan lingkungan berdasarkan observasi tersebut sebelum melakukan eksekusi manifest modul melalui Unified Tool Interface.
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <h2 className="font-serif text-3xl font-semibold mb-8 text-center text-stone-900">Menjaga Keseimbangan Tradisi</h2>
          <p className="text-center text-lg mb-12 text-stone-500 max-w-2xl mx-auto font-light">Kami memastikan teknologi tidak merusak tradisi. Algoritma kami dirancang untuk menjaga keseimbangan sesuai nilai leluhur.</p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 mb-20">
            <div className="text-center group">
              <div className="bg-stone-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6 border border-stone-100 group-hover:scale-110 transition-transform">
                <Heart className="w-6 h-6 text-red-700" />
              </div>
              <h4 className="font-serif text-xl font-semibold mb-3 text-stone-800">Parahyangan</h4>
              <p className="text-xs text-stone-400 leading-relaxed font-light">Menjaga kesucian area pura agar tetap terjaga dari pembangunan ilegal.</p>
            </div>
            <div className="text-center group">
              <div className="bg-stone-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6 border border-stone-100 group-hover:scale-110 transition-transform">
                <Scale className="w-6 h-6 text-stone-600" />
              </div>
              <h4 className="font-serif text-xl font-semibold mb-3 text-stone-800">Pawongan</h4>
              <p className="text-xs text-stone-400 leading-relaxed font-light">Menjaga keharmonisan warga dengan memastikan keadilan tata ruang.</p>
            </div>
            <div className="text-center group">
              <div className="bg-stone-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6 border border-stone-100 group-hover:scale-110 transition-transform">
                <Shield className="w-6 h-6 text-green-800" />
              </div>
              <h4 className="font-serif text-xl font-semibold mb-3 text-stone-800">Palemahan</h4>
              <p className="text-xs text-stone-400 leading-relaxed font-light">Menjaga kelestarian alam agar tetap hijau dan asri untuk masa depan.</p>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
