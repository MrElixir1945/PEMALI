import { AlertTriangle, AlertCircle, Info, Activity } from "lucide-react";
import Link from "next/link";

interface ScoreCardProps {
  region: string;
  priority: string;
  justification: string;
  ndviChange: number;
  awareness: number;
}

export default function ScoreCard({ region, priority, justification, ndviChange, awareness }: ScoreCardProps) {
  const getStyle = () => {
    switch (priority) {
      case "DARURAT_MERAH":
        return { bg: "bg-red-50", border: "border-red-200", text: "text-red-700", icon: <AlertTriangle className="text-red-600" />, badge: "bg-red-100 text-red-800" };
      case "PRIORITAS_TINGGI":
        return { bg: "bg-orange-50", border: "border-orange-200", text: "text-orange-700", icon: <AlertCircle className="text-orange-600" />, badge: "bg-orange-100 text-orange-800" };
      case "KLARIFIKASI_INFORMASI":
        return { bg: "bg-yellow-50", border: "border-yellow-200", text: "text-yellow-700", icon: <Info className="text-yellow-600" />, badge: "bg-yellow-100 text-yellow-800" };
      default:
        return { bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-700", icon: <Activity className="text-emerald-600" />, badge: "bg-emerald-100 text-emerald-800" };
    }
  };

  const style = getStyle();

  return (
    <div className={`rounded-xl border ${style.border} ${style.bg} p-6 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-white rounded-lg shadow-sm">
            {style.icon}
          </div>
          <div>
            <h3 className="font-bold text-lg text-slate-900 capitalize">{region}</h3>
            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${style.badge} mt-1`}>
              {priority.replace("_", " ")}
            </span>
          </div>
        </div>
      </div>
      
      <p className="mt-4 text-sm text-slate-700 leading-relaxed font-medium">
        {justification}
      </p>

      <div className="mt-6 grid grid-cols-2 gap-4">
        <div className="bg-white rounded-lg p-3 border border-slate-100 shadow-sm">
          <p className="text-xs text-slate-500 font-medium">NDVI Change</p>
          <p className={`text-lg font-bold ${ndviChange < 0 ? 'text-red-600' : 'text-emerald-600'}`}>
            {ndviChange > 0 ? '+' : ''}{ndviChange}%
          </p>
        </div>
        <div className="bg-white rounded-lg p-3 border border-slate-100 shadow-sm">
          <p className="text-xs text-slate-500 font-medium">Awareness</p>
          <p className="text-lg font-bold text-blue-600">{awareness}/100</p>
        </div>
      </div>

      <div className="mt-6">
        <Link 
          href={`/report/${region}`}
          className="w-full inline-flex justify-center items-center px-4 py-2 text-sm font-semibold rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors"
        >
          Lihat Laporan Lengkap
        </Link>
      </div>
    </div>
  );
}
