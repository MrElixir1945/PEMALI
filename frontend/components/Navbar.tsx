import Link from "next/link";
import { Shield } from "lucide-react";

export default function Navbar() {
  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Link href="/" className="flex items-center gap-2 group">
                <div className="bg-emerald-600 text-white p-2 rounded-lg group-hover:bg-emerald-700 transition-colors">
                  <Shield size={24} />
                </div>
                <div>
                  <h1 className="font-bold text-xl text-slate-900 tracking-tight">PEMALI</h1>
                  <p className="text-[10px] uppercase font-semibold tracking-wider text-emerald-600">Geo-Audit Agent</p>
                </div>
              </Link>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <span className="inline-flex items-center rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
              Prototype v0.1
            </span>
          </div>
        </div>
      </div>
    </nav>
  );
}
