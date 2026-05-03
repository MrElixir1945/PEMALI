import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";
import CodeBlock from "@/components/CodeBlock";
import { Server, Database, Cpu, Layers } from "lucide-react";

export default function EngineeringPage() {
  const satelliteManifest = `@property
def manifest(self) -> Dict[str, Any]:
    return {
        "name": "satellite_intelligence",
        "description": "Fetch live sentinel-2 data",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string"
                }
            },
            "required": ["location"]
        }
    }`;

  return (
    <>
      <NavBar />
      <main className="flex-1 max-w-4xl mx-auto px-8 py-16 w-full text-stone-800">
        <div className="prose prose-stone max-w-none">
          <h1 className="font-serif text-5xl font-semibold mb-8 text-stone-900">Engineering</h1>
          <p className="text-xl text-stone-600 font-light leading-relaxed mb-12">
            Infrastruktur lab yang tangguh. Memanfaatkan Fedora, Proxmox, dan FastAPI untuk mengelola orkestrasi agen secara terdistribusi.
          </p>

          <div className="poleng-divider my-12"></div>

          <h2 className="font-serif text-3xl font-semibold mb-8 text-stone-800">Stack Teknologi</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 my-12 text-center">
            <div className="bg-white border border-stone-200 p-6 rounded-[2rem] shadow-sm hover:shadow-md transition-shadow">
              <Cpu className="w-8 h-8 mx-auto mb-3 text-stone-400" />
              <div className="text-[10px] font-bold uppercase tracking-wider text-stone-400">Host OS</div>
              <div className="text-sm font-medium text-stone-900">Fedora Labs</div>
            </div>
            <div className="bg-white border border-stone-200 p-6 rounded-[2rem] shadow-sm hover:shadow-md transition-shadow">
              <Server className="w-8 h-8 mx-auto mb-3 text-stone-400" />
              <div className="text-[10px] font-bold uppercase tracking-wider text-stone-400">Virtualization</div>
              <div className="text-sm font-medium text-stone-900">Proxmox VE</div>
            </div>
            <div className="bg-white border border-stone-200 p-6 rounded-[2rem] shadow-sm hover:shadow-md transition-shadow">
              <Layers className="w-8 h-8 mx-auto mb-3 text-stone-400" />
              <div className="text-[10px] font-bold uppercase tracking-wider text-stone-400">Backend</div>
              <div className="text-sm font-medium text-stone-900">FastAPI</div>
            </div>
            <div className="bg-white border border-stone-200 p-6 rounded-[2rem] shadow-sm hover:shadow-md transition-shadow">
              <Database className="w-8 h-8 mx-auto mb-3 text-stone-400" />
              <div className="text-[10px] font-bold uppercase tracking-wider text-stone-400">Database</div>
              <div className="text-sm font-medium text-stone-900">PostgreSQL</div>
            </div>
          </div>

          <h2 className="font-serif text-3xl font-semibold mb-6 text-stone-800">Unified Tool Interface (UTI)</h2>
          <p className="text-stone-600 leading-relaxed mb-8">
            Setiap modul dalam sistem PEMALI mengikuti standar Unified Tool Interface, memungkinkan orkestrator untuk memanggil alat secara dinamis berdasarkan kebutuhan audit.
          </p>

          <CodeBlock 
            code={satelliteManifest} 
            filename="modules/satellite_mod.py" 
          />

          <h2 className="font-serif text-3xl font-semibold mb-6 mt-12 text-stone-800">Infrastruktur Lab</h2>
          <p className="text-stone-600 leading-relaxed">
            Sistem berjalan di lingkungan lab terisolasi yang dioptimalkan untuk beban kerja AI agentic. Pipeline data dari sensor satelit diproses secara paralel oleh worker node untuk menjamin latensi rendah dalam pelaporan audit.
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
