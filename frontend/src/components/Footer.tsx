import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t pt-16 pb-12 mt-auto" style={{ borderColor: "var(--pemali-border)", backgroundColor: "var(--pemali-bg)" }}>
      <div className="max-w-7xl mx-auto px-8 grid grid-cols-1 md:grid-cols-4 gap-8 mb-16">
        <div className="col-span-1 md:col-span-2">
          <h2 className="font-serif text-2xl font-semibold mb-4" style={{ color: "var(--pemali-text-primary)" }}>Pemali.</h2>
          <p className="text-sm max-w-xs mb-6" style={{ color: "var(--pemali-text-muted)" }}>
            Audit Ekologi Otonom. Mengintegrasikan citra satelit dan Agentic AI untuk pengawasan bentang alam secara real-time.
          </p>
          <Link href="/dashboard" className="text-sm font-semibold transition-colors inline-flex items-center" style={{ color: "var(--pemali-text-primary)" }}>
            Enter the System <span className="ml-1">→</span>
          </Link>
        </div>
        
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--pemali-text-muted)" }}>Technology</h4>
          <ul className="space-y-3 text-sm" style={{ color: "var(--pemali-text-secondary)" }}>
            <li><span className="transition-colors cursor-pointer hover:opacity-70">FastAPI Core</span></li>
            <li><span className="transition-colors cursor-pointer hover:opacity-70">ReAct Framework</span></li>
            <li><span className="transition-colors cursor-pointer hover:opacity-70">Sentinel OSINT</span></li>
          </ul>
        </div>
        
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--pemali-text-muted)" }}>Platform</h4>
          <ul className="space-y-3 text-sm" style={{ color: "var(--pemali-text-secondary)" }}>
            <li><Link href="/methodology" className="transition-colors hover:opacity-70">Methodology</Link></li>
            <li><Link href="/engineering" className="transition-colors hover:opacity-70">Engineering</Link></li>
            <li><a href="https://github.com/mrelixir" target="_blank" rel="noreferrer" className="transition-colors hover:opacity-70">GitHub Repository</a></li>
          </ul>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-8 pt-6 flex justify-between items-center text-xs" style={{ borderTop: "1px solid var(--pemali-border)", color: "var(--pemali-text-muted)" }}>
        <p>&copy; 2026 Tim Subak Guardian.</p>
        <div className="space-x-4">
          <span>Designed for Fedoralabs</span>
        </div>
      </div>
    </footer>
  );
}
