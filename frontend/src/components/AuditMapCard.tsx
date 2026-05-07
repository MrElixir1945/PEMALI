"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Globe, Shield, Activity, Map as MapIcon, ChevronDown, ChevronUp, Share2, FileText, BarChart3, Layers } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import dynamic from "next/dynamic";

const MapContainer = dynamic(() => import('react-leaflet').then(mod => mod.MapContainer), { ssr: false });
const TileLayer = dynamic(() => import('react-leaflet').then(mod => mod.TileLayer), { ssr: false });
const Marker = dynamic(() => import('react-leaflet').then(mod => mod.Marker), { ssr: false });
const Popup = dynamic(() => import('react-leaflet').then(mod => mod.Popup), { ssr: false });
const MapUpdater = dynamic(() => Promise.resolve(({ center }: { center: [number, number] }) => {
  const { useMap } = require('react-leaflet');
  const map = useMap();
  map.setView(center, 15);
  return null;
}), { ssr: false });

const customMarkerIcon = (L: any) => new L.DivIcon({
  className: 'custom-div-icon',
  html: `
    <div style="position: relative;">
      <div style="background-color: #ef4444; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5); position: absolute; top: -7px; left: -7px; z-index: 2;"></div>
      <div style="background-color: #ef4444; width: 14px; height: 14px; border-radius: 50%; position: absolute; top: -7px; left: -7px; animation: pulse 2s infinite; z-index: 1;"></div>
    </div>
  `,
  iconSize: [0, 0],
  iconAnchor: [0, 0]
});

interface AuditLog {
  id: number;
  location: string;
  issue: string;
  narrative: string;
  thk: string;
  ndvi_score?: number;
  ndvi_change?: number;
}



interface AuditMapCardProps {
  auditLog: AuditLog;
  memories: any[];
  setAuditLog: (log: any) => void;
  handleActionClick: (action: string) => void;
}

export default function AuditMapCard({ auditLog, memories, setAuditLog, handleActionClick }: AuditMapCardProps) {
  const [reportExpanded, setReportExpanded] = useState(false);
  const [showTechnical, setShowTechnical] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const locLower = (auditLog.location || "").toLowerCase();
  let coords: [number, number] = [-8.5069, 115.2625];
  
  if (locLower.includes("canggu") || locLower.includes("badung")) {
    coords = [-8.6478, 115.1385];
  } else if (locLower.includes("seminyak") || locLower.includes("kuta")) {
    coords = [-8.6913, 115.1682];
  } else if (locLower.includes("nusa penida") || locLower.includes("klungkung")) {
    coords = [-8.7278, 115.5444];
  } else if (locLower.includes("jatiluwih") || locLower.includes("tabanan")) {
    coords = [-8.3700, 115.1310];
  } else if (locLower.includes("sanur") || locLower.includes("denpasar")) {
    coords = [-8.6865, 115.2647];
  }

  return (
    <motion.div
      key="audit-result-card"
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.6 }}
      className="w-full max-w-4xl mx-auto bg-white border-thin rounded-2xl overflow-hidden shadow-[0_30px_60px_-15px_rgba(0,0,0,0.08)] mb-20"
    >
      <div className="aspect-[21/10] w-full bg-stone-100 relative group overflow-hidden border-b border-stone-200/50">
        {mounted && (
          <div className="absolute inset-0 z-10">
            <MapContainer
              center={coords}
              zoom={14}
              style={{ height: '100%', width: '100%' }}
              zoomControl={false}
              attributionControl={false}
            >
              <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              />
              <TileLayer
                url="https://stamen-tiles-{s}.a.ssl.fastly.net/toner-labels/{z}/{x}/{y}{r}.png"
                opacity={0.4}
              />
              <Marker
                position={coords}
                icon={typeof window !== 'undefined' ? customMarkerIcon(require('leaflet')) : undefined}
              >
                <Popup>
                  <div className="font-sans text-[10px] p-1 uppercase tracking-wider font-bold">{auditLog.location}</div>
                </Popup>
              </Marker>
              <MapUpdater center={coords} />
            </MapContainer>
          </div>
        )}

        {/* Technical Overlays */}
        <div className="absolute top-6 left-6 z-30 flex gap-2">
          <div className="bg-stone-900/90 backdrop-blur-md px-3 py-1.5 rounded flex items-center gap-2 border border-white/10 shadow-xl">
            <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div>
            <span className="text-[9px] font-bold text-white uppercase tracking-[0.2em]">Sentinel-2 Live</span>
          </div>
        </div>

        <button
          onClick={() => setAuditLog(null)}
          className="absolute top-6 right-6 z-30 w-9 h-9 bg-white/20 backdrop-blur-md rounded-full border border-white/20 text-white hover:bg-white/40 transition-all flex items-center justify-center shadow-xl"
        >
          <ChevronUp className="w-4 h-4" />
        </button>
      </div>

      <div className="p-12 space-y-12">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-8">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className={`w-1.5 h-1.5 rounded-full ${auditLog.issue.includes('Kritis') ? 'bg-red-500' : 'bg-green-500'}`}></div>
              <span className="text-[10px] font-bold uppercase tracking-[0.3em] text-stone-400">Status Laporan</span>
            </div>
            <h2 className="text-4xl font-serif font-medium text-stone-900 tracking-tight leading-tight max-w-xl">
              {auditLog.issue.includes('Kritis') ? 'Kawasan Lindung Terancam' : 'Kawasan Dalam Pengawasan'}
            </h2>
            <div className="flex items-center gap-2 text-stone-400 text-xs font-medium uppercase tracking-wider">
              <Globe className="w-3.5 h-3.5 opacity-50" /> {auditLog.location}
            </div>
          </div>

          <div className="flex flex-col items-end">
            <div className="text-[10px] font-bold uppercase tracking-[0.3em] text-stone-300 mb-2">Philosophy Alignment</div>
            <div className="text-stone-900 font-serif text-lg">{auditLog.thk}</div>
          </div>
        </div>

        <div className="pt-12 border-t border-stone-100">
          <div className="flex items-center gap-3 mb-8">
             <FileText className="w-4 h-4 text-stone-300" />
             <h3 className="text-[10px] font-bold text-stone-400 uppercase tracking-[0.3em]">Hasil Analisis Lengkap</h3>
          </div>
          
          <div className="prose max-w-3xl">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {auditLog.narrative}
            </ReactMarkdown>
          </div>
        </div>

        <div className="pt-12 border-t border-stone-100 grid grid-cols-1 md:grid-cols-2 gap-12">
          <div>
            <h4 className="text-[10px] font-bold uppercase text-stone-400 tracking-[0.3em] mb-6 flex items-center gap-2">
              <BarChart3 className="w-3.5 h-3.5 opacity-50" /> Analisis Spektral
            </h4>
            <div className="space-y-6">
              <div className="flex justify-between items-end border-b border-stone-100 pb-3">
                <span className="text-[10px] text-stone-400 font-bold uppercase tracking-widest">NDVI Score</span>
                <span className="text-2xl font-serif text-stone-900">{auditLog.ndvi_score || "0.42"}</span>
              </div>
              <div className="flex justify-between items-end border-b border-stone-100 pb-3">
                <span className="text-[10px] text-stone-400 font-bold uppercase tracking-widest">Vegetation Delta</span>
                <span className="text-lg font-serif text-red-500">{auditLog.ndvi_change || "-12.5"}%</span>
              </div>
            </div>
          </div>
          
          <div className="flex flex-col justify-end gap-4">
             <div className="flex gap-4">
                <button onClick={() => handleActionClick("Bagikan")} className="flex-1 px-6 py-3 bg-stone-50 hover:bg-stone-100 text-stone-600 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all border-thin">
                  Bagikan
                </button>
                <button onClick={() => handleActionClick("Download PDF")} className="flex-1 px-6 py-3 bg-stone-50 hover:bg-stone-100 text-stone-600 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all border-thin">
                  Export PDF
                </button>
             </div>
             <button
               onClick={() => handleActionClick("Sertifikat Digital")}
               className="w-full px-6 py-4 bg-stone-900 text-white rounded-lg text-[10px] font-bold uppercase tracking-widest hover:bg-stone-800 transition-all flex items-center justify-center gap-3"
             >
               <Shield className="w-4 h-4 text-stone-400" /> Ambil Sertifikat Audit
             </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
