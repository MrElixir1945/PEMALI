import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";
import Terminal from "@/components/Terminal";
import { Eye, Brain, FileText, ChevronRight } from "lucide-react";
import Link from "next/link";

export default function Home() {
  return (
    <>
      <NavBar />
      <main className="flex-1 max-w-7xl mx-auto px-8 w-full">
        {/* Hero Section */}
        <section className="pt-20 pb-24 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7">
            <div className="inline-flex items-center space-x-2 bg-stone-100/50 px-3 py-1 rounded-full border border-stone-200/50 mb-6">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              <span className="text-[10px] text-stone-500 font-mono uppercase tracking-wider">Agentic Network Online</span>
            </div>
            
            <h1 className="font-serif text-5xl md:text-7xl font-semibold leading-[1.05] tracking-tight mb-8 text-stone-900">
              Audit Ekologi <span className="text-stone-500 italic">Otonom.</span>
            </h1>
            <p className="text-xl text-stone-600 font-light max-w-xl leading-relaxed mb-10">
              Mengintegrasikan citra satelit dan Agentic AI untuk pengawasan bentang alam secara real-time. Melindungi Bali dengan kecerdasan digital.
            </p>
            <div className="flex flex-col sm:flex-row items-start sm:items-center space-y-4 sm:space-y-0 sm:space-x-6">
              <Link href="/dashboard" className="bg-stone-900 text-white px-8 py-4 rounded-full text-sm font-medium hover:bg-black transition-all shadow-lg flex items-center group">
                Mulai Audit Sekarang
                <ChevronRight className="ml-2 w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
              <div className="flex items-center space-x-4 px-4 py-2 border-l border-stone-200">
                <div className="flex -space-x-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="w-8 h-8 rounded-full border-2 border-white bg-stone-100 flex items-center justify-center overflow-hidden">
                      <div className="w-full h-full bg-stone-200"></div>
                    </div>
                  ))}
                </div>
                <div className="text-[11px] text-stone-400 font-mono leading-tight">
                  <span className="block text-stone-600 font-bold">14+ Nodes</span>
                  Distribusi Regional
                </div>
              </div>
            </div>
          </div>
          
          <div className="lg:col-span-5">
            <Terminal />
          </div>
        </section>

        <div className="poleng-divider my-8"></div>

        {/* Simplified Workflow Section */}
        <section className="py-24">
          <div className="text-center mb-16">
            <h2 className="font-serif text-4xl font-semibold mb-4">Melihat, Berpikir, Melindungi.</h2>
            <p className="text-stone-500 max-w-2xl mx-auto">PEMALI bekerja seperti detektif digital untuk menjaga Bali agar tetap hijau sesuai dengan nilai leluhur kita.</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            <div className="flex flex-col items-center text-center p-8 bg-white rounded-3xl border border-stone-100 shadow-sm transition-all hover:shadow-xl hover:-translate-y-1">
              <div className="bg-stone-50 w-16 h-16 rounded-2xl flex items-center justify-center mb-8 rotate-3 group-hover:rotate-0 transition-transform">
                <Eye className="w-8 h-8 text-stone-800" />
              </div>
              <h3 className="font-serif text-xl font-semibold mb-4">Melihat dari Langit</h3>
              <p className="text-sm text-stone-600 leading-relaxed">
                PEMALI menggunakan mata satelit untuk memantau kesehatan hutan dan lahan di Bali secara langsung dari angkasa.
              </p>
            </div>
            
            <div className="flex flex-col items-center text-center p-8 bg-white rounded-3xl border border-stone-100 shadow-sm transition-all hover:shadow-xl hover:-translate-y-1">
              <div className="bg-stone-50 w-16 h-16 rounded-2xl flex items-center justify-center mb-8 -rotate-3 group-hover:rotate-0 transition-transform">
                <Brain className="w-8 h-8 text-stone-800" />
              </div>
              <h3 className="font-serif text-xl font-semibold mb-4">Menganalisis Masalah</h3>
              <p className="text-sm text-stone-600 leading-relaxed">
                AI akan membandingkan apa yang ia lihat dengan aturan yang berlaku untuk memastikan tidak ada pelanggaran alam.
              </p>
            </div>
            
            <div className="flex flex-col items-center text-center p-8 bg-white rounded-3xl border border-stone-100 shadow-sm transition-all hover:shadow-xl hover:-translate-y-1">
              <div className="bg-stone-50 w-16 h-16 rounded-2xl flex items-center justify-center mb-8 rotate-6 group-hover:rotate-0 transition-transform">
                <FileText className="w-8 h-8 text-stone-800" />
              </div>
              <h3 className="font-serif text-xl font-semibold mb-4">Memberikan Laporan</h3>
              <p className="text-sm text-stone-600 leading-relaxed">
                Setelah yakin, sistem akan otomatis membuat rangkuman audit yang siap digunakan oleh pihak berwenang.
              </p>
            </div>
          </div>
          
          <div className="mt-16 text-center">
            <Link href="/methodology" className="text-sm font-medium text-stone-500 hover:text-stone-900 transition-colors inline-flex items-center">
              Pelajari Cara Kerja Detektif Kami <ChevronRight className="ml-1 w-3 h-3" />
            </Link>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
