"use client";

import useSWR from "swr";
import Navbar from "@/components/Navbar";
import NDVIChart from "@/components/NDVIChart";
import AwarenessGauge from "@/components/AwarenessGauge";
import THKReport from "@/components/THKReport";
import { ArrowLeft, MapPin, Satellite, Users, BookOpen } from "lucide-react";
import Link from "next/link";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function RegionReport({ params }: { params: { region: string } }) {
  const { data, error, isLoading } = useSWR(`http://localhost:8000/audit/${params.region}`, fetcher);

  if (isLoading) return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div></div>;
  if (error) return <div className="min-h-screen flex items-center justify-center p-8"><div className="bg-red-50 text-red-600 p-4 rounded-lg">Gagal memuat data.</div></div>;
  if (!data) return null;

  return (
    <div className="bg-slate-50 min-h-screen pb-12">
      <Navbar />
      
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <div>
          <Link href="/" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-slate-900 transition-colors mb-6">
            <ArrowLeft className="w-4 h-4" /> Kembali ke Dashboard
          </Link>
          
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <MapPin className="text-emerald-600 w-8 h-8" />
                <h2 className="text-4xl font-black text-slate-900 capitalize tracking-tight">{data.region}</h2>
              </div>
              <p className="text-slate-500 text-lg">Laporan Audit Agen PEMALI berdasarkan Data Satelit & Sentimen Sosial.</p>
            </div>
            
            <div className={`px-4 py-2 rounded-lg border font-bold text-sm shadow-sm ${
              data.priority.priority === 'DARURAT_MERAH' ? 'bg-red-100 text-red-800 border-red-200' :
              data.priority.priority === 'PRIORITAS_TINGGI' ? 'bg-orange-100 text-orange-800 border-orange-200' :
              data.priority.priority === 'KLARIFIKASI_INFORMASI' ? 'bg-yellow-100 text-yellow-800 border-yellow-200' :
              'bg-emerald-100 text-emerald-800 border-emerald-200'
            }`}>
              STATUS: {data.priority.priority.replace('_', ' ')}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* SATELLITE MODULE */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-100">
              <div className="p-2 bg-blue-50 text-blue-600 rounded-lg"><Satellite /></div>
              <div>
                <h3 className="font-bold text-lg">Kondisi Fisik (Satelit)</h3>
                <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Modul 1: NDVI Change</p>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4 mb-8">
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                <p className="text-xs text-slate-500 font-bold uppercase mb-1">Perubahan</p>
                <p className={`text-3xl font-black ${data.satellite.change_pct < 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                  {data.satellite.change_pct}%
                </p>
              </div>
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                <p className="text-xs text-slate-500 font-bold uppercase mb-1">Status Fisik</p>
                <p className="text-lg font-bold text-slate-800 leading-tight">
                  {data.satellite.status.replace(/_/g, ' ')}
                </p>
              </div>
            </div>

            <h4 className="font-bold text-sm text-slate-700 mb-4">Tren NDVI 6 Bulan Terakhir</h4>
            <NDVIChart data={data.satellite.history} baseline={data.satellite.ndvi_baseline} />
          </div>

          {/* OSINT MODULE */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-100">
              <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg"><Users /></div>
              <div>
                <h3 className="font-bold text-lg">Kesadaran Sosial (OSINT)</h3>
                <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Modul 2: Media Sosial</p>
              </div>
            </div>

            <AwarenessGauge score={data.osint.awareness_score} />

            <div className="mt-8 grid grid-cols-2 gap-4">
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-100 text-center">
                <p className="text-2xl font-black text-slate-800">{data.osint.total_posts}</p>
                <p className="text-[10px] uppercase font-bold text-slate-500">Total Post Diperiksa</p>
              </div>
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-100 text-center">
                <p className="text-2xl font-black text-indigo-600">{data.osint.env_mentions}</p>
                <p className="text-[10px] uppercase font-bold text-slate-500">Isu Lingkungan</p>
              </div>
            </div>

            <div className="mt-6">
              <h4 className="font-bold text-xs uppercase text-slate-500 mb-3">Top Keywords</h4>
              <div className="flex flex-wrap gap-2">
                {data.osint.top_keywords.map((kw: string) => (
                  <span key={kw} className="bg-slate-100 text-slate-700 px-3 py-1 rounded-full text-xs font-semibold">
                    #{kw}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* POLICY MODULE */}
        <div className="bg-white p-6 md:p-8 rounded-2xl border border-slate-200 shadow-sm mt-8">
          <div className="flex items-center gap-3 mb-8">
            <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg"><BookOpen /></div>
            <div>
              <h3 className="font-bold text-2xl text-slate-900">Analisis Kebijakan</h3>
              <p className="text-sm text-slate-500 uppercase tracking-wider font-semibold">Modul 4: Evaluasi Tri Hita Karana</p>
            </div>
          </div>
          
          <THKReport 
            violations={data.policy.thk_violations} 
            recommendation={data.policy.recommendation} 
          />
        </div>
      </main>
    </div>
  );
}
