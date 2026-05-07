"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, User, Shield, Terminal as TerminalIcon, Loader2, Plus, PanelLeftClose, PanelLeftOpen, WifiOff, CheckCircle } from "lucide-react";
import NavBar from "@/components/NavBar";
import IdleCanvas from "@/components/IdleCanvas";
import ReasoningCanvas, { ReasoningStep } from "@/components/ReasoningCanvas";
import AuditMapCard from "@/components/AuditMapCard";
import DocumentPreviewModal from "@/components/DocumentPreviewModal";
import PemaliMascot from "@/components/PemaliMascot";

interface Memory { id: number; role: string; content: string; name?: string; }
interface AuditLog { id: number; session_id?: string; location: string; issue: string; narrative: string; thk: string; ndvi_score?: number; ndvi_change?: number; timestamp?: string; }
interface SystemStatus { worker_active: boolean; tasks: any[]; recent_audits: AuditLog[]; modules?: any[]; }

export default function DashboardPage() {
  const [prompt, setPrompt] = useState("");
  const [memories, setMemories] = useState<Memory[]>([]);
  const [auditLog, setAuditLog] = useState<AuditLog | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [backendError, setBackendError] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [previewDoc, setPreviewDoc] = useState<{ type: 'pdf' | 'cert', content: any } | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const logEndRef = useRef<HTMLDivElement>(null);
  const prevMemoriesLength = useRef(0);

  const fetchData = async () => {
    try {
      const statusRes = await fetch("/api/status").catch(() => null);
      if (statusRes && statusRes.ok) {
        const statusData = await statusRes.json();
        setStatus(prevStatus => {
          if (!prevStatus || !isTyping) return statusData;
          const currentAuditId = prevStatus.recent_audits?.[0]?.id;
          if (currentAuditId && currentAuditId > 1000000000000) {
             const found = statusData.recent_audits?.some((a: any) => a.id === currentAuditId || a.session_id === sessionId);
             if (!found) {
                return { ...statusData, recent_audits: [prevStatus.recent_audits[0], ...(statusData.recent_audits || [])] };
             }
          }
          return statusData;
        });
        setBackendError(false);
      } else {
        setBackendError(true);
      }

      if (sessionId === "NEW") return;
      const fetchUrl = sessionId ? `/api/session?session_id=${sessionId}` : "/api/session";
      const res = await fetch(fetchUrl).catch(() => null);
      if (!res || !res.ok) return;
      const data = await res.json();
      if (!data || !data.session_id) return;

      if (sessionId !== data.session_id) {
        setSessionId(data.session_id);
        setMemories([]);
        setAuditLog(null);
        prevMemoriesLength.current = 0;
      }

      const newMemories = data.memories || [];
      setMemories(newMemories);
      setAuditLog(data.audit_log || null);

      if (newMemories.length > prevMemoriesLength.current) {
        logEndRef.current?.scrollIntoView({ behavior: "smooth" });
        prevMemoriesLength.current = newMemories.length;
      }
      
      const lastMem = newMemories[newMemories.length - 1];
      if (data.audit_log || (lastMem && lastMem.role === "assistant")) {
        setIsTyping(false);
      }
    } catch (e) {
      console.error("Fetch error", e);
      setBackendError(true);
    }
  };

  useEffect(() => {
    setMounted(true);
    fetchData();
    const interval = setInterval(fetchData, isTyping ? 1500 : 4000);
    return () => clearInterval(interval);
  }, [sessionId, isTyping]);

  const handleSend = async () => {
    if (!prompt.trim() || backendError) return;
    setIsTyping(true);
    const p = prompt;
    setPrompt("");

    const userMem: Memory = { id: Date.now(), role: "user", content: p };
    setMemories(prev => [...prev, userMem]);

    if (status) {
      const tempAudit: AuditLog = {
        id: Date.now(), location: p, issue: "Audit Baru", narrative: "Sedang menganalisis kawasan...", thk: "Pending", timestamp: new Date().toISOString()
      };
      setStatus({ ...status, recent_audits: [tempAudit, ...(status.recent_audits || [])] });
    }

    try {
      const res = await fetch("/api/trigger", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prompt: p, session_id: sessionId }),
      });
      const data = await res.json();
      if (data && data.session_id) setSessionId(data.session_id);
      setTimeout(fetchData, 1000);
    } catch (e) {
      console.error("Trigger error", e);
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
      prevMemoriesLength.current = data.memories?.length || 0;
    } catch (e) {}
  };

  const handleActionClick = (action: string) => {
    if (action === "Download PDF") setPreviewDoc({ type: 'pdf', content: auditLog });
    else if (action === "Ambil Sertifikat" || action === "Sertifikat Digital") setPreviewDoc({ type: 'cert', content: auditLog });
    else if (action === "Bagikan") {
      if (navigator.share) navigator.share({ title: `Audit PEMALI — ${auditLog?.location}`, url: window.location.href }).catch(() => {});
      else navigator.clipboard.writeText(window.location.href).then(() => { setToast("✓ Link berhasil disalin"); setTimeout(() => setToast(null), 3000); });
    } else alert(`${action} belum tersedia.`);
  };

  const handleNewChat = () => {
    setSessionId("NEW"); setMemories([]); setAuditLog(null); setIsTyping(false); prevMemoriesLength.current = 0;
  };

  if (!mounted) return null;

  // Determine App State
  let appState: 'idle' | 'thinking' | 'done' = 'idle';
  const hasTools = memories.some(m => m.role === 'tool');
  
  if (auditLog) {
    appState = 'done';
  } else if (hasTools || (isTyping && memories.length > 2)) { 
    // Show reasoning only if tools are involved or if it's a deep process
    appState = 'thinking';
  } else {
    appState = 'idle';
  }

  // Derive reasoning steps from tool memories if in thinking mode
  const steps: ReasoningStep[] = [
    { id: "orchestrator", label: "PEMALI Orchestrator", sublabel: "Memproses instruksi", icon: "🧠", status: 'done' }
  ];
  if (appState === 'thinking') {
    const toolMems = memories.filter(m => m.role === 'tool');
    const sysMems = memories.filter(m => m.role === 'system');

    const getStatus = (name: string, prevDone?: boolean) => {
      const mems = toolMems.filter(m => m.name === name);
      if (mems.length === 0) return prevDone ? 'active' : 'pending';
      const last = mems[mems.length - 1];
      return last.content === "started" ? 'active' : 'done';
    };

    const orchestratorDone = sysMems.some(m => m.name === 'orchestrator');
    
    steps[0].status = orchestratorDone ? 'done' : 'active';
    
    const satStatus = getStatus('satellite_audit', orchestratorDone);
    const osintStatus = getStatus('osint_intel', satStatus === 'done');
    const commStatus = getStatus('community_engagement', osintStatus === 'done');
    const repStatus = getStatus('reporting_mod', commStatus === 'done');

    // Data Processing is active if orchestrator is done but tools haven't finished yet
    const dataDone = satStatus === 'done' && osintStatus === 'done' && commStatus === 'done';
    
    steps.push({ id: "data_processing", label: "Pengolahan Data", sublabel: "Menyiapkan UI & Konteks", icon: "⚙️", status: dataDone ? 'done' : (orchestratorDone ? 'active' : 'pending') });
    steps.push({ id: "satellite", label: "Satellite Module", sublabel: "Akuisisi Sentinel-2", icon: "🛰", status: satStatus });
    steps.push({ id: "osint", label: "OSINT Module", sublabel: "Pencarian intelijen", icon: "📡", status: osintStatus });
    steps.push({ id: "community", label: "Community Module", sublabel: "Data keterlibatan sosial", icon: "👥", status: commStatus });
    steps.push({ id: "reporting", label: "Reporting Module", sublabel: "Sintesis laporan THK", icon: "📋", status: repStatus });
    
    steps.push({ id: "final_output", label: "Output Laporan", sublabel: "Finalisasi Data", icon: "📑", status: repStatus === 'done' ? 'active' : 'pending' });
  }

  // Determine Mascot State
  let mascotState: "idle" | "running" | "thinking" | "writing" | "done" = "idle";
  if (appState === "done") mascotState = "done";
  else if (appState === "thinking") {
    // If it's early in the process (many pending), it's running.
    // If it's in the middle, it's thinking.
    // If it's at the end (reporting), it's writing.
    const activeStep = steps.find(s => s.status === 'active');
    if (activeStep?.id === 'data_processing' || activeStep?.id === 'satellite') mascotState = "running";
    else if (activeStep?.id === 'osint' || activeStep?.id === 'community') mascotState = "thinking";
    else mascotState = "writing";
  }

  return (
    <div className="flex flex-col min-h-screen bg-[#F7F6F3] text-stone-900 font-sans selection:bg-stone-200 overflow-hidden h-screen">
      <NavBar />
      
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }}
            className="fixed top-20 right-6 z-[200] bg-stone-900 text-white text-sm font-medium px-5 py-3 rounded-2xl shadow-lg flex items-center gap-2"
          >
            <CheckCircle className="w-4 h-4 text-green-400" />{toast}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Layout */}
      <main className="flex-1 flex w-full overflow-hidden relative">
        
        {/* LEFT SIDEBAR - HISTORY (Desktop) */}
        <div className="hidden lg:flex flex-col w-64 border-r border-stone-200/50 bg-stone-50/50 overflow-hidden z-20">
          <div className="p-6">
            <div className="font-serif text-xl tracking-tight mb-8">Pemali.</div>
            <button onClick={handleNewChat} className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-stone-900 text-white rounded-lg text-xs font-medium hover:bg-stone-800 transition-all">
              <Plus className="w-4 h-4" /> New Audit
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-1">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-stone-400 mb-4 px-2">History</div>
            {status?.recent_audits?.map((audit, idx) => (
              <div
                key={`audit-${audit.id || idx}`}
                onClick={() => audit.session_id && handleLoadSession(audit.session_id)}
                className={`w-full p-2.5 rounded-lg cursor-pointer transition-all ${
                  sessionId === audit.session_id ? "bg-stone-200/50 text-stone-900" : "bg-transparent text-stone-500 hover:bg-stone-100"
                }`}
              >
                <div className="text-[10px] font-bold uppercase tracking-wider truncate mb-0.5">{audit.issue || "Audit"}</div>
                <div className="text-xs truncate opacity-80">{audit.location}</div>
              </div>
            ))}
          </div>
        </div>

        {/* MAIN CANVAS - Middle */}
        <div className="flex-1 flex flex-col bg-white overflow-hidden relative border-r border-stone-200/50 z-10">
          <AnimatePresence mode="wait">
            {appState === 'idle' && (
              <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full">
                <IdleCanvas />
              </motion.div>
            )}
            
            {appState === 'thinking' && (
              <motion.div key="thinking" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full">
                <ReasoningCanvas steps={steps} isVisible={true} mascotState={mascotState as "running" | "thinking" | "writing"} />
              </motion.div>
            )}

            {appState === 'done' && auditLog && (
              <motion.div key="done" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full overflow-y-auto px-6 lg:px-12 py-12">
                <AuditMapCard auditLog={auditLog} memories={memories} setAuditLog={setAuditLog} handleActionClick={handleActionClick} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* RIGHT SIDEBAR - CHAT */}
        <motion.div
          initial={false}
          animate={{ width: sidebarOpen ? (typeof window !== 'undefined' && window.innerWidth < 1024 ? '100%' : 400) : 0, opacity: sidebarOpen ? 1 : 0 }}
          transition={{ duration: 0.2 }}
          className="bg-[#FAF9F6] flex flex-col overflow-hidden relative flex-shrink-0 z-20"
        >
          {/* Sidebar Header */}
          <div className="p-5 flex items-center justify-between z-10">
            <div className="flex items-center gap-2.5">
              <div className="w-1.5 h-1.5 rounded-full bg-stone-900 animate-pulse"></div>
              <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-stone-400">PEMALI Network Online</span>
            </div>
          </div>

          {/* Chat Messages Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
             {memories.map((mem, idx) => {
                if (mem.role === "system") return null;
                const isUser = mem.role === "user";
                const isTool = mem.role === "tool";

                if (isTool) {
                   return (
                     <div key={`mem-${idx}`} className="flex gap-3 opacity-50">
                       <TerminalIcon className="w-3.5 h-3.5 text-stone-400 mt-1 flex-shrink-0" />
                       <div className="text-[10px] font-mono text-stone-500 uppercase tracking-wider">
                          {mem.name} processed
                       </div>
                     </div>
                   );
                }

                return (
                  <div key={`mem-${idx}`} className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
                    <div className={`max-w-[90%] px-4 py-3 text-[13px] leading-relaxed ${
                      isUser
                        ? "bg-stone-900 text-stone-50 rounded-2xl rounded-tr-sm"
                        : "bg-white border border-stone-200/60 text-stone-800 rounded-2xl rounded-tl-sm shadow-sm"
                    }`}>
                      {mem.content.includes("# LAPORAN AUDIT") || mem.content.includes("RINGKASAN EKSEKUTIF") 
                         ? "Audit ekologi selesai. Hasil analisis dapat ditinjau pada Canvas Utama." 
                         : mem.content}
                    </div>
                    {!isUser && idx === memories.length - 1 && (
                      <div className="mt-2 text-[10px] uppercase tracking-widest text-stone-300 ml-4">Assistant</div>
                    )}
                  </div>
                );
             })}
             
             {isTyping && (
                <div className="flex flex-col items-start">
                  <div className="bg-white border border-stone-200/60 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm flex items-center gap-2">
                    <div className="flex space-x-1.5">
                      <div className="w-1 h-1 bg-stone-300 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                      <div className="w-1 h-1 bg-stone-300 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                      <div className="w-1 h-1 bg-stone-300 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
                    </div>
                  </div>
                </div>
             )}

             {/* Final Audit Report Card in Chat */}
             {appState === 'done' && auditLog && (
               <motion.div 
                 initial={{ opacity: 0, y: 10 }} 
                 animate={{ opacity: 1, y: 0 }}
                 className="mt-8 flex flex-col items-center gap-6 py-8 border-t border-stone-200/50"
               >
                 <div className="text-center px-4">
                    <p className="font-serif text-base text-stone-700 leading-relaxed italic mb-6">
                      &ldquo;Analisis kawasan {auditLog.location} telah dirampungkan dengan status {auditLog.issue}.&rdquo;
                    </p>
                    <div className="flex flex-col items-center gap-4">
                      <PemaliMascot state="done" size={90} />
                      <div className="text-[10px] font-bold uppercase tracking-[0.3em] text-stone-300">
                        Audit Certified
                      </div>
                    </div>
                 </div>
               </motion.div>
             )}
             <div ref={logEndRef} className="h-4" />
          </div>

          {/* Input Box */}
          <div className="p-6 bg-transparent z-10">
             <div className="relative">
               <input
                 type="text"
                 value={prompt}
                 onChange={(e) => setPrompt(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && handleSend()}
                 placeholder={backendError ? "Offline..." : (isTyping ? "Memproses..." : "Ketik instruksi audit...")}
                 disabled={isTyping || backendError}
                 className="w-full bg-white border border-stone-200/80 rounded-2xl py-3.5 pl-5 pr-14 text-[13px] focus:outline-none focus:border-stone-900 transition-all shadow-sm disabled:opacity-50"
               />
               <button
                 onClick={handleSend}
                 disabled={isTyping || backendError}
                 className="absolute right-2.5 top-1/2 -translate-y-1/2 w-9 h-9 bg-stone-900 text-white rounded-xl flex items-center justify-center hover:bg-stone-800 transition-all disabled:opacity-50"
               >
                 {isTyping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
               </button>
             </div>
          </div>
        </motion.div>
      </main>

      <DocumentPreviewModal previewDoc={previewDoc} setPreviewDoc={setPreviewDoc} sessionId={sessionId} />
    </div>
  );
}
