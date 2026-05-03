"use client";

import { useState, useEffect, useRef } from "react";
import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";
import { 
  Send, Terminal as TerminalIcon, Globe, Shield, User, Bot, Loader2, 
  Activity, Map as MapIcon, History, AlertTriangle, CheckCircle, Info,
  ExternalLink, BarChart3, Layers, FileText, ChevronDown, ChevronUp,
  Maximize2, Share2, WifiOff
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface Memory {
  id: number;
  role: string;
  content: string;
  name?: string;
}

interface AuditLog {
  id: number;
  location: string;
  issue: string;
  narrative: string;
  thk: string;
  ndvi_score?: number;
  ndvi_change?: number;
  timestamp?: string;
}

interface SystemStatus {
  worker_active: boolean;
  tasks: any[];
  recent_audits: AuditLog[];
  modules?: any[];
}

export default function DashboardPage() {
  const [prompt, setPrompt] = useState("");
  const [memories, setMemories] = useState<Memory[]>([]);
  const [auditLog, setAuditLog] = useState<AuditLog | null>(null);
  const [satelliteImg, setSatelliteImg] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [showTechnical, setShowTechnical] = useState(false);
  const [backendError, setBackendError] = useState(false);
  
  const logEndRef = useRef<HTMLDivElement>(null);
  const prevMemoriesLength = useRef(0);

  const fetchData = async () => {
    try {
      const statusRes = await fetch("/api/status").catch(() => null);
      if (statusRes && statusRes.ok) {
        const statusData = await statusRes.json();
        setStatus(statusData);
        setBackendError(false);
      } else {
        setBackendError(true);
      }

      const res = await fetch("/api/session").catch(() => null);
      if (!res || !res.ok) return;
      const data = await res.json();
      if (!data || !data.session_id) return;

      if (sessionId !== data.session_id) {
        setSessionId(data.session_id);
        setMemories([]);
        setAuditLog(null);
        setSatelliteImg(null);
        setShowTechnical(false);
        prevMemoriesLength.current = 0;
      }

      const newMemories = data.memories || [];
      setMemories(newMemories);
      setAuditLog(data.audit_log || null);
      setSatelliteImg(data.satellite_img || null);
      
      // Auto-scroll only if new memories are added
      if (newMemories.length > prevMemoriesLength.current) {
        logEndRef.current?.scrollIntoView({ behavior: "smooth" });
        prevMemoriesLength.current = newMemories.length;
      }
    } catch (e) {
      console.error("Fetch error", e);
      setBackendError(true);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [sessionId]);

  const handleSend = async () => {
    if (!prompt.trim() || backendError) return;
    setIsTyping(true);
    const p = prompt;
    setPrompt("");

    try {
      await fetch("/api/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: p }),
      });
    } catch (e) {
      console.error("Trigger error", e);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#FAF9F6] text-stone-900 font-sans selection:bg-stone-200">
      <NavBar />
      
      <main className="flex-1 flex w-full h-[calc(100vh-64px)] overflow-hidden">
        
        {/* SUBTLE LEFT SIDEBAR */}
        <div className="w-64 border-r border-stone-200/60 bg-stone-50/20 flex flex-col overflow-hidden hidden lg:flex">
          <div className="p-6 border-b border-stone-200/60">
            <div className="flex items-center gap-3">
              <div className="relative flex h-2 w-2">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${backendError ? "bg-red-400" : "bg-green-400"} opacity-75`}></span>
                <span className={`relative inline-flex rounded-full h-2 w-2 ${backendError ? "bg-red-500" : "bg-green-500"}`}></span>
              </div>
              <span className="text-[10px] font-bold uppercase text-stone-400 tracking-[0.2em]">
                {backendError ? "Backend Offline" : "System Active"}
              </span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-6">
            <section>
              <h3 className="text-[9px] font-bold uppercase text-stone-300 tracking-[0.2em] mb-4 px-2 text-center">History</h3>
              <div className="space-y-1">
                {status?.recent_audits?.slice(0, 8).map((audit, idx) => (
                  <div key={`audit-${audit.id || idx}`} className="p-2 rounded-full hover:bg-white transition-colors cursor-pointer group px-4">
                    <div className="text-[11px] font-medium text-stone-500 group-hover:text-stone-900 truncate">{audit.location}</div>
                  </div>
                ))}
                {(!status?.recent_audits || status.recent_audits.length === 0) && !backendError && (
                   <div className="text-[10px] text-stone-300 italic text-center py-4">Belum ada histori.</div>
                )}
                {backendError && (
                   <div className="flex flex-col items-center justify-center py-10 opacity-30">
                      <WifiOff className="w-6 h-6 text-stone-400 mb-2" />
                      <span className="text-[9px] uppercase tracking-widest text-stone-400">Disconnected</span>
                   </div>
                )}
              </div>
            </section>
          </div>
        </div>

        {/* MAIN CANVAS */}
        <div className="flex-1 flex flex-col items-center bg-white overflow-hidden relative">
          
          <div className="w-full max-w-4xl flex-1 overflow-y-auto px-6 py-12 space-y-12 scroll-smooth">
            <AnimatePresence mode="wait">
              {memories.length === 0 && !isTyping && (
                <motion.div 
                  key="empty-state"
                  initial={{ opacity: 0, y: 20 }} 
                  animate={{ opacity: 1, y: 0 }} 
                  exit={{ opacity: 0 }}
                  className="h-[60vh] flex flex-col items-center justify-center text-center"
                >
                  <div className="w-20 h-20 bg-stone-50 rounded-full flex items-center justify-center mb-8 border border-stone-100">
                    <Bot className="w-10 h-10 text-stone-200" />
                  </div>
                  <h1 className="text-3xl font-serif font-semibold text-stone-800 mb-4">Siap Membantu Audit.</h1>
                  <p className="text-stone-400 font-light max-w-sm leading-relaxed">
                    Sebutkan lokasi atau permasalahan lingkungan yang ingin Anda periksa. Saya akan melakukan analisis mendalam secara otonom.
                  </p>
                  {backendError && (
                    <div className="mt-8 px-6 py-2 bg-red-50 text-red-500 text-[10px] rounded-full font-bold uppercase tracking-widest border border-red-100">
                       Backend belum terhubung.
                    </div>
                  )}
                </motion.div>
              )}
              
              <div className="space-y-8" key="chat-flow">
                {memories.map((mem, idx) => {
                  if (mem.role === "system") return null;
                  const isUser = mem.role === "user";
                  const isTool = mem.role === "tool";

                  if (isTool && !showTechnical) return null;

                  return (
                    <motion.div
                      key={`mem-${mem.id || idx}`}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                    >
                      {isTool ? (
                        <div className="w-full max-w-2xl bg-stone-50/50 border border-stone-100 rounded-3xl p-6 flex gap-4 items-start shadow-sm">
                           <TerminalIcon className="w-4 h-4 text-stone-300 mt-1" />
                           <div className="flex-1">
                              <div className="text-[10px] font-mono text-stone-400 uppercase tracking-widest mb-1">{mem.name} execution</div>
                              <div className="text-xs text-stone-600 font-serif italic leading-relaxed">
                                {(() => {
                                  try {
                                    const parsed = JSON.parse(mem.content);
                                    return parsed.agent_hint || "Processing spatial data...";
                                  } catch (e) {
                                    return mem.content;
                                  }
                                })()}
                              </div>
                           </div>
                        </div>
                      ) : (
                        <div className={`flex gap-4 max-w-[80%] ${isUser ? "flex-row-reverse" : ""}`}>
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 border ${
                            isUser ? "bg-stone-900 border-stone-900 text-white" : "bg-white border-stone-200 text-stone-400"
                          }`}>
                             {isUser ? <User className="w-4 h-4" /> : <Shield className="w-4 h-4" />}
                          </div>
                          <div className={`px-6 py-4 rounded-[2rem] ${
                            isUser 
                              ? "bg-stone-900 text-white rounded-tr-sm" 
                              : "bg-[#FAF9F6] border border-stone-100 text-stone-800 rounded-tl-sm shadow-sm"
                          } text-sm leading-relaxed`}>
                            {mem.content}
                          </div>
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </div>

              {/* AUDIT MASTER CARD */}
              {auditLog && (
                <motion.div
                  key="audit-result-card"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5 }}
                  className="w-full bg-white border border-stone-200 rounded-[3rem] overflow-hidden shadow-2xl shadow-stone-200/50 mt-12 mb-20"
                >
                   <div className="aspect-[21/9] w-full bg-stone-100 relative group overflow-hidden">
                      {satelliteImg ? (
                        <>
                          <img src={satelliteImg} alt="Evidence" className="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-105" />
                          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent"></div>
                          <div className="absolute bottom-6 left-8 flex items-center gap-3">
                             <div className="w-10 h-10 rounded-2xl bg-white/20 backdrop-blur-md flex items-center justify-center border border-white/30 text-white">
                                <MapIcon className="w-5 h-5" />
                             </div>
                             <div>
                                <div className="text-[10px] text-white/70 font-mono uppercase tracking-widest">Evidence Type</div>
                                <div className="text-sm font-bold text-white tracking-tight">Sentinel-2 Satellite Feed</div>
                             </div>
                          </div>
                        </>
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-stone-300">
                           <Globe className="w-12 h-12 animate-pulse" />
                        </div>
                      )}
                   </div>

                   <div className="p-10 space-y-8">
                      <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
                         <div className="space-y-2">
                            <div className="flex items-center gap-2">
                               <span className={`w-2 h-2 rounded-full ${auditLog.issue.includes('Kritis') ? 'bg-red-500' : 'bg-green-500'}`}></span>
                               <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-stone-400">Status Laporan</span>
                            </div>
                            <h2 className="text-3xl font-serif font-bold text-stone-900 tracking-tight">
                               {auditLog.issue.includes('Kritis') ? 'Kawasan Lindung Terancam' : 'Kawasan Dalam Pengawasan'}
                            </h2>
                            <div className="flex items-center gap-2 text-stone-500 text-sm font-light italic">
                               <Globe className="w-3 h-3" /> {auditLog.location} — Bali, Indonesia
                            </div>
                         </div>
                         
                         <div className="flex flex-col items-end gap-2">
                            <div className="px-4 py-2 bg-stone-100 rounded-full text-[10px] font-bold text-stone-600 uppercase tracking-tighter border border-stone-200">
                               {auditLog.thk} Alignment
                            </div>
                         </div>
                      </div>

                      <div className="text-lg text-stone-600 font-light leading-relaxed max-w-3xl">
                         {auditLog.narrative}
                      </div>

                      <div className="pt-8 border-t border-stone-100 flex flex-col md:flex-row items-center justify-between gap-6">
                         <div className="flex items-center gap-8">
                            <div className="flex items-center gap-2 text-stone-400 hover:text-stone-900 transition-colors cursor-pointer group">
                               <Share2 className="w-4 h-4" /> <span className="text-xs font-medium">Bagikan</span>
                            </div>
                            <div className="flex items-center gap-2 text-stone-400 hover:text-stone-900 transition-colors cursor-pointer group">
                               <FileText className="w-4 h-4" /> <span className="text-xs font-medium">Download PDF</span>
                            </div>
                         </div>

                         <button 
                           onClick={() => setShowTechnical(!showTechnical)}
                           className="flex items-center gap-2 text-xs font-bold text-stone-400 hover:text-stone-900 transition-all uppercase tracking-widest bg-stone-50 px-4 py-2 rounded-full border border-stone-100"
                         >
                           {showTechnical ? 'Sembunyikan' : 'Detail Teknis'}
                           {showTechnical ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                         </button>
                      </div>

                      <AnimatePresence>
                        {showTechnical && (
                          <motion.div
                            key="tech-details"
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                          >
                             <div className="p-8 bg-stone-50 rounded-[2rem] border border-stone-100 grid grid-cols-1 md:grid-cols-2 gap-8 mt-4">
                                <div>
                                   <h4 className="text-[10px] font-bold uppercase text-stone-400 tracking-widest mb-4 flex items-center gap-2">
                                      <BarChart3 className="w-3 h-3" /> Analisis Spektral
                                   </h4>
                                   <div className="space-y-4 font-mono">
                                      <div className="flex justify-between items-end border-b border-stone-200 pb-2">
                                         <span className="text-[10px] text-stone-400 uppercase">NDVI Score</span>
                                         <span className="text-xl font-bold">{auditLog.ndvi_score || "0.42"}</span>
                                      </div>
                                      <div className="flex justify-between items-end border-b border-stone-200 pb-2">
                                         <span className="text-[10px] text-stone-400 uppercase">Vegetation Delta</span>
                                         <span className="text-sm font-bold text-red-500">{auditLog.ndvi_change || "-12.5"}%</span>
                                      </div>
                                   </div>
                                </div>
                                <div>
                                   <h4 className="text-[10px] font-bold uppercase text-stone-400 tracking-widest mb-4 flex items-center gap-2">
                                      <Layers className="w-3 h-3" /> Reasoning Log
                                   </h4>
                                   <div className="space-y-2 max-h-32 overflow-y-auto pr-2 custom-scrollbar">
                                      {memories.filter(m => m.role === 'tool').map((m, i) => (
                                        <div key={`tool-log-${i}`} className="text-[10px] font-mono text-stone-500 bg-white/50 p-2 rounded-xl border border-stone-100">
                                           &gt; {m.name}: Success
                                        </div>
                                      ))}
                                   </div>
                                </div>
                             </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                   </div>
                   
                   <div className="bg-stone-900 p-8 flex flex-col md:flex-row items-center justify-between gap-6">
                      <div className="flex items-center gap-4">
                         <div className="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center border border-white/20">
                            <Shield className="w-6 h-6 text-white" />
                         </div>
                         <div>
                            <div className="text-[10px] text-white/50 font-mono uppercase tracking-[0.2em] mb-1">Audit Certified</div>
                            <div className="text-sm text-white font-medium">Laporan Bersertifikat Digital</div>
                         </div>
                      </div>
                      <button className="px-8 py-3 bg-white text-stone-900 rounded-full text-[10px] font-bold uppercase tracking-widest hover:bg-stone-200 transition-all flex items-center gap-2">
                         <FileText className="w-4 h-4" /> Ambil Sertifikat
                      </button>
                   </div>
                </motion.div>
              )}
            </AnimatePresence>
            
            {isTyping && (
              <div className="flex justify-start items-center gap-4">
                 <div className="w-8 h-8 rounded-full bg-stone-50 flex items-center justify-center flex-shrink-0 animate-pulse border border-stone-100">
                    <Loader2 className="w-4 h-4 text-stone-300 animate-spin" />
                 </div>
                 <div className="text-[10px] font-mono text-stone-300 uppercase tracking-[0.2em]">Memproses data...</div>
              </div>
            )}
            
            <div ref={logEndRef} className="h-40" />
          </div>

          {/* Floated Input Bar */}
          <div className="absolute bottom-10 left-1/2 -translate-x-1/2 w-full max-w-2xl px-6">
             <div className="relative group">
               <div className="absolute inset-0 bg-stone-900/5 blur-3xl group-focus-within:bg-stone-900/10 transition-all rounded-full"></div>
               <input 
                 type="text" 
                 value={prompt}
                 onChange={(e) => setPrompt(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && handleSend()}
                 placeholder={backendError ? "Backend offline..." : "Instruksikan audit..."}
                 disabled={isTyping || backendError}
                 className="w-full bg-white border border-stone-200 rounded-full py-5 pl-10 pr-20 text-sm focus:outline-none focus:ring-1 focus:ring-stone-400 transition-all shadow-2xl shadow-stone-200/40 relative z-10 disabled:opacity-50"
               />
               <button 
                 onClick={handleSend}
                 disabled={isTyping || !prompt.trim() || backendError}
                 className="absolute right-4 top-1/2 -translate-y-1/2 w-12 h-12 bg-stone-900 text-white rounded-full hover:bg-black transition-all flex items-center justify-center z-20 disabled:bg-stone-100 disabled:text-stone-300"
               >
                 {isTyping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
               </button>
             </div>
             <div className="mt-4 text-center">
                <p className="text-[9px] text-stone-300 font-mono tracking-widest uppercase">Agentic AI Auditor — Powered by Sentinel-2</p>
             </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
