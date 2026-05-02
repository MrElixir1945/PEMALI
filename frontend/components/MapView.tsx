"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";

// Memuat komponen Map secara dinamis (client-side only) karena Leaflet butuh window
const Map = dynamic(() => import("./Map"), { 
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[400px] bg-slate-100 animate-pulse flex items-center justify-center rounded-xl border border-slate-200">
      <span className="text-slate-400 font-medium flex flex-col items-center gap-2">
        <svg className="w-8 h-8 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Memuat Peta Satelit...
      </span>
    </div>
  )
});

interface MapViewProps {
  data: any[];
}

export default function MapView({ data }: MapViewProps) {
  return (
    <div className="w-full h-[500px] rounded-xl overflow-hidden border border-slate-200 shadow-sm relative z-0">
      <Map data={data} />
    </div>
  );
}
