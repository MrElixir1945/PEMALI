import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";
import { Shield, Microscope, Scale, RefreshCw } from "lucide-react";

export default function MethodologyPage() {
  return (
    <>
      <NavBar />
      <main className="flex-1 max-w-4xl mx-auto px-8 py-16 w-full">
        <div className="prose prose-stone max-w-none">
          <h1 className="font-serif text-5xl font-semibold mb-8">Methodology</h1>
          <p className="text-xl text-stone-600 font-light leading-relaxed mb-12">
            Sistem berbasis ReAct (Reasoning & Acting). Setiap audit melalui fase observasi spasial, validasi hukum, dan penilaian dampak lingkungan sebelum menghasilkan laporan final.
          </p>

          <div className="poleng-divider my-12"></div>

          <h2 className="font-serif text-3xl font-semibold mb-6">Siklus ReAct</h2>
          <p>
            PEMALI mengadopsi kerangka kerja ReAct yang memungkinkan model bahasa besar (LLM) untuk melakukan penalaran (Reasoning) dan pengambilan tindakan (Acting) secara bergantian.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 my-12">
            <div className="bg-white border border-stone-200 p-6 rounded-2xl shadow-sm">
              <div className="bg-stone-100 w-10 h-10 rounded-lg flex items-center justify-center mb-4">
                <Microscope className="w-5 h-5 text-stone-600" />
              </div>
              <h3 className="font-serif text-xl font-semibold mb-2">Observation</h3>
              <p className="text-sm text-stone-600">Agen mengamati lingkungan melalui alat yang tersedia, seperti integrasi citra satelit Sentinel-2 untuk mendapatkan data NDVI terkini.</p>
            </div>
            <div className="bg-white border border-stone-200 p-6 rounded-2xl shadow-sm">
              <div className="bg-stone-100 w-10 h-10 rounded-lg flex items-center justify-center mb-4">
                <RefreshCw className="w-5 h-5 text-stone-600" />
              </div>
              <h3 className="font-serif text-xl font-semibold mb-2">Reasoning</h3>
              <p className="text-sm text-stone-600">Berdasarkan hasil observasi, agen menganalisis data untuk menentukan langkah selanjutnya, memvalidasi hipotesis kerusakan lingkungan.</p>
            </div>
          </div>

          <h2 className="font-serif text-3xl font-semibold mb-6">Harmonisasi Tri Hita Karana</h2>
          <p>
            Kami mentransformasikan nilai filosofis Bali ke dalam algoritma audit yang objektif.
          </p>
          
          <div className="space-y-6 my-8">
            <div className="flex gap-6 items-start">
              <div className="bg-[#2F4F4F] p-3 rounded-full mt-1">
                <Shield className="w-4 h-4 text-white" />
              </div>
              <div>
                <h4 className="font-serif text-lg font-semibold mb-1">Palemahan (Ekologi)</h4>
                <p className="text-sm text-stone-600">Pengawasan otonom terhadap kelestarian alam, penggunaan lahan, dan tutupan vegetasi melalui sensor satelit.</p>
              </div>
            </div>
            <div className="flex gap-6 items-start">
              <div className="bg-stone-800 p-3 rounded-full mt-1">
                <Scale className="w-4 h-4 text-white" />
              </div>
              <div>
                <h4 className="font-serif text-lg font-semibold mb-1">Pawongan (Sosial & Hukum)</h4>
                <p className="text-sm text-stone-600">Audit kepatuhan terhadap regulasi tata ruang dan kroscek data OSINT untuk memitigasi konflik kepentingan.</p>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
