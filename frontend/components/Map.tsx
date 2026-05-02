"use client";

import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import Link from "next/link";
import { useEffect } from "react";
import L from "leaflet";

const REGION_COORDS: Record<string, [number, number]> = {
  bedugul: [-8.275, 115.158],
  ubud: [-8.506, 115.262],
  buleleng: [-8.112, 115.088],
};

const getMarkerColor = (priority: string) => {
  switch (priority) {
    case "DARURAT_MERAH": return "#dc2626"; // red-600
    case "PRIORITAS_TINGGI": return "#ea580c"; // orange-600
    case "KLARIFIKASI_INFORMASI": return "#ca8a04"; // yellow-600
    default: return "#059669"; // emerald-600
  }
};

export default function Map({ data }: { data: any[] }) {
  // Fix Leaflet icons issue in Next.js
  useEffect(() => {
    delete (L.Icon.Default.prototype as any)._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png',
      iconUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png',
    });
  }, []);

  return (
    <MapContainer 
      center={[-8.409518, 115.188919]} 
      zoom={10} 
      style={{ height: "100%", width: "100%", zIndex: 0 }}
      zoomControl={false}
    >
      <TileLayer
        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        attribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
      />
      {/* Semi-transparent overlay to make markers pop more */}
      <div className="absolute inset-0 bg-slate-900/20 pointer-events-none z-[400]" />

      {data.map((item, idx) => {
        const coords = REGION_COORDS[item.region];
        if (!coords) return null;
        
        const color = getMarkerColor(item.priority.priority);
        
        return (
          <CircleMarker
            key={idx}
            center={coords}
            radius={24}
            pathOptions={{ 
              color: color, 
              fillColor: color, 
              fillOpacity: 0.7,
              weight: 3
            }}
          >
            <Popup className="custom-popup">
              <div className="p-1 min-w-[200px]">
                <h3 className="font-bold text-lg capitalize mb-1">{item.region}</h3>
                <div className="flex items-center gap-2 mb-3">
                  <span className="w-3 h-3 rounded-full" style={{ backgroundColor: color }}></span>
                  <span className="text-xs font-semibold text-slate-600">
                    {item.priority.priority.replace("_", " ")}
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-2 mb-4 text-sm">
                  <div className="bg-slate-50 p-2 rounded">
                    <div className="text-slate-500 text-[10px] uppercase font-bold">NDVI</div>
                    <div className="font-semibold">{item.satellite.ndvi_current}</div>
                  </div>
                  <div className="bg-slate-50 p-2 rounded">
                    <div className="text-slate-500 text-[10px] uppercase font-bold">Awareness</div>
                    <div className="font-semibold">{item.osint.awareness_score}</div>
                  </div>
                </div>
                
                <Link 
                  href={`/report/${item.region}`}
                  className="block w-full text-center bg-emerald-600 text-white text-sm py-2 rounded font-medium hover:bg-emerald-700 transition"
                >
                  Detail Audit
                </Link>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
