import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-stone-200 pt-16 pb-12 bg-white mt-auto">
      <div className="max-w-7xl mx-auto px-8 grid grid-cols-1 md:grid-cols-4 gap-8 mb-16">
        <div className="col-span-1 md:col-span-2">
          <h2 className="font-serif text-2xl font-semibold mb-4">Pemali.</h2>
          <p className="text-sm text-stone-500 max-w-xs mb-6">
            Audit Ekologi Otonom. Mengintegrasikan citra satelit dan Agentic AI untuk pengawasan bentang alam secara real-time.
          </p>
          <Link href="/dashboard" className="text-sm font-semibold text-stone-900 hover:text-[#2F4F4F] transition-colors inline-flex items-center">
            Enter the System <span className="ml-1">→</span>
          </Link>
        </div>
        
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-stone-400 mb-4">Technology</h4>
          <ul className="space-y-3 text-sm text-stone-600">
            <li><span className="hover:text-stone-900 transition-colors cursor-pointer">FastAPI Core</span></li>
            <li><span className="hover:text-stone-900 transition-colors cursor-pointer">ReAct Framework</span></li>
            <li><span className="hover:text-stone-900 transition-colors cursor-pointer">Sentinel OSINT</span></li>
          </ul>
        </div>
        
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-stone-400 mb-4">Platform</h4>
          <ul className="space-y-3 text-sm text-stone-600">
            <li><Link href="/methodology" className="hover:text-stone-900 transition-colors">Methodology</Link></li>
            <li><Link href="/engineering" className="hover:text-stone-900 transition-colors">Engineering</Link></li>
            <li><a href="https://github.com/mrelixir" target="_blank" rel="noreferrer" className="hover:text-stone-900 transition-colors">GitHub Repository</a></li>
          </ul>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-8 pt-6 border-t border-stone-100 flex justify-between items-center text-xs text-stone-400">
        <p>&copy; 2026 Tim Subak Guardian.</p>
        <div className="space-x-4">
          <span>Designed for Fedoralabs</span>
        </div>
      </div>
    </footer>
  );
}
