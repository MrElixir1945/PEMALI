"use client";

import { useEffect, useState } from "react";

interface Task { id: number; intent: string; status: string; }
interface StatusData { worker_active: boolean; tasks: Task[]; }

export default function Terminal() {
  const [data, setData] = useState<StatusData | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch("/api/status");
        if (!res.ok) throw new Error("Failed to fetch");
        setData(await res.json());
        setError(false);
      } catch { setError(true); }
    };
    fetchStatus();
    const iv = setInterval(fetchStatus, 5000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div className="rounded-3xl border overflow-hidden h-[340px] flex flex-col relative" style={{ backgroundColor: "#1A1714", borderColor: "rgba(255,252,245,0.06)" }}>
      <div className="px-6 py-4 flex items-center border-b" style={{ borderColor: "rgba(255,252,245,0.04)" }}>
        <div className="flex space-x-1.5">
          {[1, 2, 3].map((i) => <div key={i} className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: "#6B6760" }} />)}
        </div>
        <span className="ml-4 text-[10px] font-mono" style={{ color: "#9B9690" }}>worker.py — status check</span>
      </div>
      <div className="p-6 font-mono text-xs leading-relaxed overflow-y-auto flex-1" style={{ color: "#D4CFC6" }}>
        <div style={{ color: "#6B6760" }} className="mb-2"># Initializing Agentic Orchestrator...</div>
        <div className="mb-1" style={{ color: "#9B9690" }}>[Registry] Loaded: satellite_intelligence</div>
        <div className="mb-1" style={{ color: "#9B9690" }}>[Registry] Loaded: spatial_verifier</div>
        <div className="mb-1" style={{ color: "#9B9690" }}>[Registry] Loaded: environmental_analyzer</div>
        <div className="mb-4" style={{ color: "#6B6760" }}>[System] Background scheduler standing by.</div>
        <div className="mb-1" style={{ color: "#9B9690" }}>&gt; Pinging DB for autonomous tasks...</div>

        {error ? (
          <div style={{ color: "#D4956A" }}>[Error] Backend connection refused.</div>
        ) : !data ? (
          <div className="animate-pulse" style={{ color: "#9B9690" }}>Waiting for heartbeat...</div>
        ) : (
          <div>
            <div className="mb-3">
              {data.worker_active
                ? <span><span style={{ color: "#7A9A78" }}>[Worker]</span> Active heartbeat detected. Process running.</span>
                : <span><span style={{ color: "#D4956A" }}>[Worker]</span> Idle. Awaiting instructions...</span>
              }
            </div>
            {data.tasks && data.tasks.length > 0 && (
              <div className="mt-4 pt-3" style={{ borderTop: "1px solid rgba(255,252,245,0.04)" }}>
                <div className="mb-2" style={{ color: "#6B6760" }}># Recent Activity</div>
                {data.tasks.slice(0, 3).map((t, idx) => (
                  <div key={idx} className="flex justify-between items-center mb-1">
                    <span className="truncate max-w-[250px]" style={{ color: "#E8E6E1" }}>{t.intent}</span>
                    <span className="px-3 py-0.5 rounded-full text-[9px] font-bold" style={{ backgroundColor: t.status === "completed" ? "rgba(122,154,120,0.10)" : "rgba(212,149,106,0.10)", color: t.status === "completed" ? "#7A9A78" : "#D4956A" }}>{t.status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      <div className="absolute bottom-0 left-0 w-full h-16 pointer-events-none" style={{ background: "linear-gradient(to top, #1A1714, transparent)" }} />
    </div>
  );
}
