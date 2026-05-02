"use client";

import useSWR from "swr";
import Navbar from "@/components/Navbar";
import MapView from "@/components/MapView";
import ScoreCard from "@/components/ScoreCard";
import { Activity } from "lucide-react";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function Home() {
  const { data, error, isLoading } = useSWR("http://localhost:8000/audit/all", fetcher);

  return (
    <>
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h2 className="text-3xl font-black text-slate-900 tracking-tight">Geo-Audit Dashboard</h2>
            <p className="text-slate-500 mt-2 text-lg">Pemantauan wilayah Bali berdasarkan integrasi Satelit & OSINT.</p>
          </div>
          <div className="flex items-center gap-2 bg-emerald-50 text-emerald-700 px-4 py-2 rounded-lg border border-emerald-200">
            <Activity className="w-5 h-5 animate-pulse" />
            <span className="font-semibold text-sm">System Active: Monitoring 3 Regions</span>
          </div>
        </div>

        {isLoading && (
          <div className="h-64 flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-lg border border-red-200">
            Gagal memuat data dari server backend. Pastikan FastAPI berjalan.
          </div>
        )}

        {data && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2">
              <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
                <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                  <span className="w-2 h-6 bg-emerald-500 rounded-full inline-block"></span>
                  Peta Prioritas Penanganan
                </h3>
                <MapView data={data} />
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="font-bold text-lg flex items-center gap-2">
                <span className="w-2 h-6 bg-slate-800 rounded-full inline-block"></span>
                Urgensi Wilayah
              </h3>
              <div className="space-y-4">
                {data
                  .sort((a: any, b: any) => a.priority.urgency_rank - b.priority.urgency_rank)
                  .map((item: any) => (
                    <ScoreCard
                      key={item.region}
                      region={item.region}
                      priority={item.priority.priority}
                      justification={item.priority.justification}
                      ndviChange={item.satellite.change_pct}
                      awareness={item.osint.awareness_score}
                    />
                  ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
