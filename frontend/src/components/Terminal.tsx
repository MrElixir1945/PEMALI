"use client";

import { useEffect, useState } from "react";

interface Task {
  id: number;
  intent: string;
  status: string;
}

interface StatusData {
  worker_active: boolean;
  tasks: Task[];
}

export default function Terminal() {
  const [data, setData] = useState<StatusData | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/status');
        if (!res.ok) throw new Error("Failed to fetch");
        const json = await res.json();
        setData(json);
        setError(false);
      } catch (err) {
        setError(true);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-[#1A1A1A] rounded-3xl border border-stone-800 shadow-2xl overflow-hidden h-[340px] flex flex-col relative">
      <div className="bg-[#111111] px-6 py-4 flex items-center border-b border-stone-800/50">
        <div className="flex space-x-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-stone-600"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-stone-600"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-stone-600"></div>
        </div>
        <span className="ml-4 text-[10px] font-mono text-stone-500">worker.py — status check</span>
      </div>
      <div className="p-6 font-mono text-xs text-green-400/90 leading-relaxed overflow-y-auto flex-1">
        <div className="text-stone-500 mb-2"># Initializing Agentic Orchestrator...</div>
        <div className="mb-1 text-stone-400">[Registry] Loaded: satellite_intelligence</div>
        <div className="mb-1 text-stone-400">[Registry] Loaded: spatial_verifier</div>
        <div className="mb-1 text-stone-400">[Registry] Loaded: environmental_analyzer</div>
        <div className="mb-4 text-stone-500">[System] Background scheduler standing by.</div>
        
        <div className="text-stone-400 mb-1">&gt; Pinging DB for autonomous tasks...</div>
        
        {error ? (
          <div className="text-red-400">[Error] Backend connection refused.</div>
        ) : !data ? (
          <div className="animate-pulse text-stone-400">Waiting for heartbeat...</div>
        ) : (
          <div>
            <div className="mb-3">
              {data.worker_active ? (
                <span><span className="text-blue-400">[Worker]</span> Active heartbeat detected. Process running.</span>
              ) : (
                <span><span className="text-yellow-400">[Worker]</span> Idle. Awaiting instructions...</span>
              )}
            </div>
            
            {data.tasks && data.tasks.length > 0 && (
              <div className="mt-4 border-t border-stone-800 pt-3">
                <div className="text-stone-500 mb-2"># Recent Activity</div>
                {data.tasks.slice(0, 3).map((t, idx) => (
                  <div key={idx} className="flex justify-between items-center mb-1">
                    <span className="text-stone-300 truncate max-w-[250px]">{t.intent}</span>
                    <span className={`px-3 py-0.5 rounded-full text-[9px] font-bold ${
                      t.status === 'completed' ? 'bg-green-900/30 text-green-400' : 'bg-yellow-900/30 text-yellow-400'
                    }`}>
                      {t.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      <div className="absolute bottom-0 left-0 w-full h-16 bg-gradient-to-t from-[#1A1A1A] to-transparent pointer-events-none"></div>
    </div>
  );
}
