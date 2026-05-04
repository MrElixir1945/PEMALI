"use client";

import { useState, useEffect, useRef } from "react";
import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";
import { 
  Send, Terminal as TerminalIcon, Globe, Shield, User, Bot, Loader2, 
  Activity, Map as MapIcon, History, AlertTriangle, CheckCircle, Info,
  ExternalLink, BarChart3, Layers, FileText, ChevronDown, ChevronUp,
  Maximize2, Share2, WifiOff, PanelLeftClose, PanelLeftOpen, Plus
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
  const [mounted, setMounted] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  const logEndRef = useRef<HTMLDivElement>(null);
  const prevMemoriesLength = useRef(0);

  const fetchData = async () => {
    try {
      const statusRes = await fetch("/api/status").catch(() => null);
      if (statusRes && statusRes.ok) {
        const statusData = await statusRes.json();
        setStatus(statusData);
        setBackendError(false);
        // If worker is no longer active, stop the typing indicator
        if (!statusData.worker_active) {
          setIsTyping(false);
        }
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
    setMounted(true);
    fetchData();
    // Adaptive polling: fast (1.5s) when AI is active, slow (4s) when idle
    const interval = setInterval(fetchData, isTyping ? 1500 : 4000);
    return () => clearInterval(interval);
  }, [sessionId, isTyping]);

  const handleSend = async () => {
    if (!prompt.trim() || backendError) return;
    setIsTyping(true);
    const p = prompt;
    setPrompt("");

    // Optimistic update memories
    const userMem: Memory = { id: Date.now(), role: "user", content: p };
    setMemories(prev => [...prev, userMem]);

    // Optimistic update history sidebar
    if (status) {
      const tempAudit: AuditLog = {
        id: Date.now(),
        location: p,
        issue: "Audit Baru",
        narrative: "Sedang menganalisis kawasan...",
        thk: "Pending",
        timestamp: new Date().toISOString()
      };
      setStatus({
        ...status,
        recent_audits: [tempAudit, ...(status.recent_audits || [])]
      });
    }

    try {
      await fetch("/api/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: p }),
      });
      // Immediate fetch to catch the new session
      setTimeout(fetchData, 1000);
    } catch (e) {
      console.error("Trigger error", e);
    } finally {
      setIsTyping(false);
    }
  };

  const handleLoadSession = async (sid: string) => {
    if (sid === sessionId) return;
    try {
      const res = await fetch(`/api/session?session_id=${sid}`);
      if (!res.ok) return;
      const data = await res.json();
      
      setSessionId(data.session_id);
      setMemories(data.memories || []);
      setAuditLog(data.audit_log || null);
      setSatelliteImg(data.satellite_img || null);
      setShowTechnical(false);
      prevMemoriesLength.current = data.memories?.length || 0;
      
      // Scroll to top when loading new session
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      console.error("Load session error", e);
    }
  };

  const handleActionClick = (action: string) => {
    if (action === "Ambil Sertifikat") {
      const win = window.open("", "_blank");
      if (win) {
        win.document.write(`
          <html>
            <head>
              <title>Digital Audit Certificate - PEMALI</title>
              <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;700&display=swap" rel="stylesheet">
              <style>
                body { font-family: "Inter", sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #FAF9F6; margin: 0; }
                .cert { width: 800px; padding: 60px; background: white; border: 20px solid #2F4F4F; box-shadow: 0 40px 100px rgba(0,0,0,0.1); position: relative; text-align: center; }
                .cert::before { content: ""; position: absolute; top: 10px; left: 10px; right: 10px; bottom: 10px; border: 2px solid #2F4F4F; pointer-events: none; }
                h1 { font-family: "Playfair Display", serif; font-size: 48px; color: #1a1a1a; margin-bottom: 10px; }
                .subtitle { text-transform: uppercase; letter-spacing: 4px; font-size: 12px; color: #888; font-weight: 700; margin-bottom: 40px; }
                .content { font-size: 18px; line-height: 1.6; color: #444; }
                .location { font-weight: 700; color: #1a1a1a; font-size: 24px; margin: 20px 0; }
                .signature { margin-top: 60px; border-top: 1px solid #ddd; display: inline-block; padding-top: 10px; width: 200px; }
                .footer { margin-top: 40px; font-size: 10px; color: #aaa; text-transform: uppercase; letter-spacing: 2px; }
              </style>
            </head>
            <body>
              <div class="cert">
                <div class="subtitle">Official Environmental Audit</div>
                <h1>Certificate of Compliance</h1>
                <div class="content">This is to certify that an autonomous ecological audit was conducted at</div>
                <div class="location">${auditLog?.location || "Unknown Location"}</div>
                <div class="content">The findings have been recorded and verified by the PEMALI Agentic AI System.</div>
                <div class="signature">PEMALI AI Auditor</div>
                <div class="footer">Verified via Sentinel-2 Satellite Data</div>
              </div>
              <script>window.print();</script>
            </body>
          </html>
        `);
        win.document.close();
      }
    } else if (action === "Bagikan") {
      if (navigator.share) {
        navigator.share({
          title: "Hasil Audit PEMALI",
          text: `Audit lingkungan di ${auditLog?.location} berhasil diverifikasi.`,
          url: window.location.href
        });
      } else {
        alert("Link audit telah disalin ke clipboard!");
      }
    } else {
      alert(`${action} fitur sedang dikembangkan untuk versi production.`);
    }
  };

  const handleNewChat = () => {
    setSessionId(null);
    setMemories([]);
    setAuditLog(null);
    setSatelliteImg(null);
    setIsTyping(false); // Fix stuck bug
    prevMemoriesLength.current = 0;
  };

  if (!mounted) return null;

  return (
    <div className="flex flex-col min-h-screen bg-[#FAF9F6] text-stone-900 font-sans selection:bg-stone-200 overflow-hidden h-screen">
      <NavBar />
      
      <main className="flex-1 flex w-full h-[calc(100vh-64px)] overflow-hidden relative">
        
        {/* SIDEBAR TOGGLE BUTTON */}
        <button 
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className={`absolute top-6 left-6 z-50 p-2 bg-white border border-stone-200 rounded-xl shadow-sm hover:bg-stone-50 transition-all ${sidebarOpen ? 'lg:hidden' : 'flex'}`}
        >
          {sidebarOpen ? <PanelLeftClose className="w-5 h-5 text-stone-500" /> : <PanelLeftOpen className="w-5 h-5 text-stone-500" />}
        </button>

        {/* SUBTLE LEFT SIDEBAR */}
        <motion.div 
          initial={false}
          animate={{ width: sidebarOpen ? 256 : 0, opacity: sidebarOpen ? 1 : 0 }}
          className="border-r border-stone-200/60 bg-stone-50/20 flex flex-col overflow-hidden hidden lg:flex relative"
        >
          <div className="p-6 border-b border-stone-200/60 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
              <span className="text-[10px] font-bold uppercase tracking-widest text-stone-400">System Active</span>
            </div>
            <button onClick={() => setSidebarOpen(false)}>
              <PanelLeftClose className="w-4 h-4 text-stone-300 hover:text-stone-900 transition-colors" />
            </button>
          </div>

          <div className="p-4">
            <button 
              onClick={handleNewChat}
              className="w-full flex items-center gap-3 px-4 py-3 bg-white border border-stone-200 rounded-2xl text-[11px] font-bold uppercase tracking-widest text-stone-600 hover:border-stone-400 hover:text-stone-900 transition-all shadow-sm"
            >
              <Plus className="w-4 h-4" /> New Chat
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-6">
            <section>
              <h3 className="text-[9px] font-bold uppercase text-stone-300 tracking-[0.2em] mb-4 px-2 text-center">History</h3>
              <div className="space-y-1">
                {status?.recent_audits?.slice(0, 15).map((audit, idx) => (
                  <div 
                    key={`audit-${audit.id || idx}`} 
                    onClick={() => audit.id && handleLoadSession(audit.timestamp ? `audit-web-${new Date(audit.timestamp).getTime()/1000}` : "")}
                    className={`p-3 rounded-2xl hover:bg-white transition-all cursor-pointer group px-4 border mb-2 ${
                      sessionId?.includes(audit.location) ? "bg-white border-stone-200 shadow-sm" : "border-transparent"
                    }`}
                  >
                    <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest mb-1 group-hover:text-stone-500 transition-colors">
                      {audit.issue || "General Audit"}
                    </div>
                    <div className="text-[11px] font-medium text-stone-500 group-hover:text-stone-900 truncate">
                      {audit.location}
                    </div>
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
        </motion.div>

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
                  <h1 className="text-3xl font-serif font-semibold text-stone-800 mb-4 tracking-tight">Siap Membantu Audit.</h1>
                  <p className="text-stone-400 font-light max-w-md leading-relaxed">
                    Sebutkan lokasi atau permasalahan lingkungan yang ingin Anda periksa. Saya akan melakukan analisis mendalam secara otonom menggunakan satelit dan data spasial.
                  </p>
                  
                  {/* CENTERED INPUT */}
                  <div className="w-full max-w-2xl mt-12 relative group px-4">
                    <div className="absolute inset-0 bg-stone-900/5 blur-3xl group-focus-within:bg-stone-900/10 transition-all rounded-full"></div>
                    <input 
                      type="text" 
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleSend()}
                      placeholder={backendError ? "Backend offline..." : (isTyping ? "Sedang memproses..." : "Instruksikan audit...")}
                      disabled={isTyping || backendError}
                      suppressHydrationWarning
                      className="w-full bg-white border border-stone-200 rounded-full py-5 pl-10 pr-20 text-sm focus:outline-none focus:ring-1 focus:ring-stone-400 transition-all shadow-2xl shadow-stone-200/40 relative z-10 disabled:opacity-50"
                    />
                    <button 
                      onClick={handleSend}
                      disabled={isTyping || backendError}
                      className="absolute right-7 top-1/2 -translate-y-1/2 w-12 h-12 bg-stone-900 text-white rounded-full flex items-center justify-center hover:bg-stone-800 transition-all z-20 shadow-lg disabled:opacity-50"
                    >
                      {isTyping ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                    </button>
                  </div>

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
                      <button 
                        onClick={() => setAuditLog(null)}
                        className="absolute top-6 right-6 z-30 w-10 h-10 bg-white/20 backdrop-blur-md rounded-full border border-white/30 text-white hover:bg-white/40 transition-all flex items-center justify-center"
                      >
                        <ChevronUp className="w-5 h-5" />
                      </button>
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
                            <div 
                              onClick={() => handleActionClick("Bagikan")}
                              className="flex items-center gap-2 text-stone-400 hover:text-stone-900 transition-colors cursor-pointer group"
                            >
                               <Share2 className="w-4 h-4" /> <span className="text-xs font-medium">Bagikan</span>
                            </div>
                            <div 
                              onClick={() => handleActionClick("Download PDF")}
                              className="flex items-center gap-2 text-stone-400 hover:text-stone-900 transition-colors cursor-pointer group"
                            >
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
                      <button 
                         onClick={() => handleActionClick("Sertifikat Digital")}
                         className="px-8 py-3 bg-white text-stone-900 rounded-full text-[10px] font-bold uppercase tracking-widest hover:bg-stone-200 transition-all flex items-center gap-2"
                       >
                         <FileText className="w-4 h-4" /> Ambil Sertifikat
                      </button>
                   </div>
                </motion.div>
              )}
            </AnimatePresence>
            
            {isTyping && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex justify-start"
              >
                <div className="flex gap-4 max-w-[80%]">
                  <div className="w-8 h-8 rounded-full bg-white border border-stone-200 text-stone-400 flex items-center justify-center flex-shrink-0">
                    <Shield className="w-4 h-4" />
                  </div>
                  <div className="bg-stone-50 border border-stone-100 rounded-[2rem] px-8 py-5 shadow-sm">
                    <div className="flex gap-2">
                      <motion.span 
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ repeat: Infinity, duration: 1.5, delay: 0 }}
                        className="w-1.5 h-1.5 bg-stone-400 rounded-full"
                      ></motion.span>
                      <motion.span 
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ repeat: Infinity, duration: 1.5, delay: 0.2 }}
                        className="w-1.5 h-1.5 bg-stone-400 rounded-full"
                      ></motion.span>
                      <motion.span 
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ repeat: Infinity, duration: 1.5, delay: 0.4 }}
                        className="w-1.5 h-1.5 bg-stone-400 rounded-full"
                      ></motion.span>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
            
            <div ref={logEndRef} className="h-40" />
          </div>

          {/* Floated Input Bar (Bottom) - Only show when chat started */}
          {memories.length > 0 && (
            <div className="absolute bottom-10 left-1/2 -translate-x-1/2 w-full max-w-2xl px-6">
               <div className="relative group">
                 <div className="absolute inset-0 bg-stone-900/5 blur-3xl group-focus-within:bg-stone-900/10 transition-all rounded-full"></div>
                 <input 
                   type="text" 
                   value={prompt}
                   onChange={(e) => setPrompt(e.target.value)}
                   onKeyDown={(e) => e.key === "Enter" && handleSend()}
                   placeholder={backendError ? "Backend offline..." : (isTyping ? "Sedang memproses..." : "Instruksikan audit...")}
                   disabled={isTyping || backendError}
                   suppressHydrationWarning
                   className="w-full bg-white border border-stone-200 rounded-full py-5 pl-10 pr-20 text-sm focus:outline-none focus:ring-1 focus:ring-stone-400 transition-all shadow-2xl shadow-stone-200/40 relative z-10 disabled:opacity-50"
                 />
                 <button 
                   onClick={handleSend}
                   disabled={isTyping || backendError}
                   className="absolute right-3 top-1/2 -translate-y-1/2 w-12 h-12 bg-stone-900 text-white rounded-full flex items-center justify-center hover:bg-stone-800 transition-all z-20 shadow-lg disabled:opacity-50"
                 >
                   {isTyping ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                 </button>
               </div>
               <div className="text-center mt-3 text-[9px] text-stone-300 font-mono uppercase tracking-[0.3em]">
                 Agentic AI Auditor — Powered by Sentinel-2
               </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
