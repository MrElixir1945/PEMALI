import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";
import Terminal from "@/components/Terminal";

export default function Home() {
  return (
    <>
      <NavBar />
      <main className="flex-1 max-w-7xl mx-auto px-8 w-full">
        {/* Hero Section */}
        <section className="pt-20 pb-24 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7">
            <h1 className="font-serif text-5xl md:text-7xl font-semibold leading-[1.05] tracking-tight mb-8">
              Audit Ekologi Otonom.
            </h1>
            <p className="text-lg text-stone-600 font-light max-w-xl leading-relaxed mb-10">
              Mengintegrasikan citra satelit dan Agentic AI untuk pengawasan bentang alam secara real-time. Membawa transparansi ekologi ke era otonom.
            </p>
            <div className="flex items-center space-x-4">
              <span className="inline-flex items-center px-3 py-1 rounded-full border border-stone-200 text-xs font-medium text-stone-600 bg-white">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 mr-2 animate-pulse"></span>
                System Online
              </span>
              <span className="text-xs text-stone-400 font-mono">Fedora Labs Active</span>
            </div>
          </div>
          
          <div className="lg:col-span-5">
            <Terminal />
          </div>
        </section>

        <div className="poleng-divider my-8"></div>

        {/* Features Section */}
        <section className="py-24">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            <div>
              <h3 className="font-serif text-xl font-semibold mb-3">Observasi Spasial</h3>
              <p className="text-sm text-stone-600 leading-relaxed">
                Penglihatan otonom melalui integrasi Sentinel-2. Mendeteksi perubahan tutupan lahan dan indeks vegetasi (NDVI) langsung dari luar angkasa.
              </p>
            </div>
            <div>
              <h3 className="font-serif text-xl font-semibold mb-3">Validasi Hukum</h3>
              <p className="text-sm text-stone-600 leading-relaxed">
                Melakukan kroscek legalitas wilayah dan tata ruang berdasarkan data pemerintah (OSINT) untuk memverifikasi status zonasi lahan hijau secara instan.
              </p>
            </div>
            <div>
              <h3 className="font-serif text-xl font-semibold mb-3">Penilaian Dampak</h3>
              <p className="text-sm text-stone-600 leading-relaxed">
                Mengkalkulasi tingkat deforestasi dan kerusakan bentang alam untuk menetapkan skala risiko ekologis dengan akurasi terukur.
              </p>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
