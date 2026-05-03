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
      <main className="flex-1 max-w-4xl mx-auto px-8 py-16 w-full">
        <div className="prose prose-stone max-w-none">
          <h1 className="font-serif text-5xl font-semibold mb-8">Engineering</h1>
          <p className="text-xl text-stone-600 font-light leading-relaxed mb-12">
            Infrastruktur lab yang tangguh. Memanfaatkan Fedora, Proxmox, dan FastAPI untuk mengelola orkestrasi agen secara terdistribusi.
          </p>

          <div className="poleng-divider my-12"></div>

          <h2 className="font-serif text-3xl font-semibold mb-6">Stack Teknologi</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 my-12 text-center">
            <div className="bg-white border border-stone-200 p-4 rounded-xl shadow-sm">
              <Cpu className="w-6 h-6 mx-auto mb-2 text-stone-400" />
              <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">Host OS</div>
              <div className="text-sm font-medium">Fedora Labs</div>
            </div>
            <div className="bg-white border border-stone-200 p-4 rounded-xl shadow-sm">
              <Server className="w-6 h-6 mx-auto mb-2 text-stone-400" />
              <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">Virtualization</div>
              <div className="text-sm font-medium">Proxmox VE</div>
            </div>
            <div className="bg-white border border-stone-200 p-4 rounded-xl shadow-sm">
              <Layers className="w-6 h-6 mx-auto mb-2 text-stone-400" />
              <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">Backend</div>
              <div className="text-sm font-medium">FastAPI</div>
            </div>
            <div className="bg-white border border-stone-200 p-4 rounded-xl shadow-sm">
              <Database className="w-6 h-6 mx-auto mb-2 text-stone-400" />
              <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">Database</div>
              <div className="text-sm font-medium">PostgreSQL</div>
            </div>
          </div>

          <h2 className="font-serif text-3xl font-semibold mb-6">Unified Tool Interface (UTI)</h2>
          <p>
            Setiap modul dalam sistem PEMALI mengikuti standar Unified Tool Interface, memungkinkan orkestrator untuk memanggil alat secara dinamis berdasarkan kebutuhan audit.
          </p>

          <CodeBlock 
            code={satelliteManifest} 
            filename="modules/satellite_mod.py" 
          />

          <h2 className="font-serif text-3xl font-semibold mb-6">Infrastruktur Lab</h2>
          <p>
            Sistem berjalan di lingkungan lab terisolasi yang dioptimalkan untuk beban kerja AI agentic. Pipeline data dari sensor satelit diproses secara paralel oleh worker node untuk menjamin latensi rendah dalam pelaporan audit.
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
