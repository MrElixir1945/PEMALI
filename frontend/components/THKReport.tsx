import { ShieldAlert, ShieldCheck } from "lucide-react";

interface THKReportProps {
  violations: any[];
  recommendation: string;
}

export default function THKReport({ violations, recommendation }: THKReportProps) {
  const isViolated = (dim: string) => violations.some(v => v.dimension === dim);
  const getDetail = (dim: string) => violations.find(v => v.dimension === dim)?.detail;

  const dimensions = [
    { name: "Parahyangan", desc: "Keseimbangan Manusia & Alam Sakral" },
    { name: "Pawongan", desc: "Keseimbangan Antar Manusia" },
    { name: "Palemahan", desc: "Keseimbangan Manusia & Lingkungan" }
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4">
        {dimensions.map(dim => {
          const violated = isViolated(dim.name);
          return (
            <div 
              key={dim.name} 
              className={`p-4 rounded-xl border flex items-start gap-4 transition-colors ${
                violated 
                  ? 'bg-red-50 border-red-200' 
                  : 'bg-emerald-50 border-emerald-200'
              }`}
            >
              <div className="mt-1">
                {violated ? (
                  <ShieldAlert className="text-red-500 w-6 h-6" />
                ) : (
                  <ShieldCheck className="text-emerald-500 w-6 h-6" />
                )}
              </div>
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <h4 className={`font-bold ${violated ? 'text-red-900' : 'text-emerald-900'}`}>
                    {dim.name}
                  </h4>
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                    violated ? 'bg-red-200 text-red-800' : 'bg-emerald-200 text-emerald-800'
                  }`}>
                    {violated ? 'TERLANGGAR' : 'AMAN'}
                  </span>
                </div>
                <p className={`text-xs font-semibold mb-2 ${violated ? 'text-red-700' : 'text-emerald-700'}`}>
                  {dim.desc}
                </p>
                {violated && (
                  <p className="text-sm text-red-800 bg-red-100/50 p-2 rounded border border-red-200/50">
                    {getDetail(dim.name)}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-slate-900 text-slate-50 p-5 rounded-xl border border-slate-800">
        <h4 className="font-bold text-sm text-slate-400 mb-2 uppercase tracking-wider">Rekomendasi Tindakan</h4>
        <p className="text-lg font-medium leading-relaxed">{recommendation}</p>
      </div>
    </div>
  );
}
