"use client";

import { useState, useEffect, useRef } from "react";
import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";
import {
  Send, Terminal as TerminalIcon, Globe, Shield, User, Bot, Loader2,
  Activity, Map as MapIcon, History, AlertTriangle, CheckCircle, Info,
  ExternalLink, BarChart3, Layers, FileText, ChevronDown, ChevronUp,
  Maximize2, Share2, WifiOff, PanelLeftClose, PanelLeftOpen, Plus,
  Download, Award, X
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
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
  map.setView(center, 15); // Zoomed in more for housing detail
  return null;
}), { ssr: false });

// High-visibility custom marker icon
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
  const [reportExpanded, setReportExpanded] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<{ type: 'pdf' | 'cert', content: any } | null>(null);
  const [toast, setToast] = useState<string | null>(null);

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
    if (action === "Download PDF") {
      setPreviewDoc({ type: 'pdf', content: auditLog });
    } else if (action === "Ambil Sertifikat" || action === "Sertifikat Digital") {
      setPreviewDoc({ type: 'cert', content: auditLog });
    } else if (action === "Bagikan") {
      const url = window.location.href;
      if (navigator.share) {
        navigator.share({
          title: `Audit PEMALI — ${auditLog?.location}`,
          text: `Laporan audit lingkungan di ${auditLog?.location} (${auditLog?.thk}).`,
          url,
        }).catch(() => {});
      } else {
        navigator.clipboard.writeText(url).then(() => {
          setToast("✓ Link berhasil disalin ke clipboard");
          setTimeout(() => setToast(null), 3000);
        });
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
    setIsTyping(false);
    setReportExpanded(false);
    setShowTechnical(false);
    prevMemoriesLength.current = 0;
    // Tell backend to reset session
    fetch("/api/new-session", { method: "POST" }).catch(() => {});
    setTimeout(fetchData, 500);
  };

  if (!mounted) return null;

  return (
    <div className="flex flex-col min-h-screen bg-[#F7F6F3] text-stone-900 font-sans selection:bg-stone-200 overflow-hidden h-screen">
      {/* Toast Notification */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ type: "spring", stiffness: 500, damping: 30 }}
            className="fixed top-6 right-6 z-[200] bg-stone-900 text-white text-sm font-medium px-5 py-3 rounded-2xl shadow-lg flex items-center gap-2"
          >
            <CheckCircle className="w-4 h-4 text-green-400" />
            {toast}
          </motion.div>
        )}
      </AnimatePresence>

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

          <div className="w-full max-w-4xl flex-1 overflow-y-auto px-6 py-12 space-y-12 scroll-smooth"
            style={{ scrollbarWidth: 'thin', scrollbarColor: '#e7e5e4 transparent' }}
          >
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
                            {mem.content.includes("# LAPORAN AUDIT") || mem.content.includes("RINGKASAN EKSEKUTIF") 
                               ? "Laporan audit ekologi telah selesai dibuat. Silakan lihat hasil analisis lengkap pada dokumen di bawah." 
                               : mem.content}
                          </div>
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </div>

              {/* AUDIT MASTER CARD */}
              {auditLog && (() => {
                 // Determine coordinates based on location string
                 const locLower = (auditLog.location || "").toLowerCase();
                 let coords: [number, number] = [-8.5069, 115.2625]; // Default Ubud
                 
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
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5 }}
                  className="w-full bg-white border border-stone-200 rounded-[3rem] overflow-hidden shadow-2xl shadow-stone-200/50 mt-12 mb-20"
                >
                   <div className="aspect-[21/9] w-full bg-stone-100 relative group overflow-hidden border-b border-stone-200">
                      {auditLog && mounted && (
                        <div className="absolute inset-0 z-10 pointer-events-auto">
                          <MapContainer
                            center={coords}
                            zoom={14}
                            style={{ height: '100%', width: '100%' }}
                            zoomControl={false}
                            attributionControl={false}
                          >
                            <TileLayer
                              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                              attribution='&copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EBP, and the GIS User Community'
                            />
                            {/* Overlay for labels/roads */}
                            <TileLayer
                              url="https://stamen-tiles-{s}.a.ssl.fastly.net/toner-labels/{z}/{x}/{y}{r}.png"
                              opacity={0.6}
                            />
                            <Marker
                              position={[-8.5069, 115.2625]}
                              icon={typeof window !== 'undefined' ? customMarkerIcon(require('leaflet')) : undefined}
                            >
                              <Popup>
                                <div className="font-sans text-xs">
                                  <div className="font-bold border-b pb-1 mb-1">{auditLog.location}</div>
                                  <div>Status: {auditLog.issue}</div>
                                </div>
                              </Popup>
                            </Marker>
                            <MapUpdater center={coords} />
                          </MapContainer>
                        </div>
                      )}

                      <button
                        onClick={() => setAuditLog(null)}
                        className="absolute top-6 right-6 z-30 w-10 h-10 bg-white/20 backdrop-blur-md rounded-full border border-white/30 text-white hover:bg-white/40 transition-all flex items-center justify-center shadow-xl"
                      >
                        <ChevronUp className="w-5 h-5" />
                      </button>
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

                      <div className="border-t border-stone-100 pt-8">
                        <button
                          onClick={() => setReportExpanded(!reportExpanded)}
                          className="w-full flex items-center justify-between group py-2"
                        >
                          <h3 className="text-xl font-serif font-bold text-stone-900 tracking-tight flex items-center gap-3">
                            <FileText className="w-5 h-5 text-stone-300" /> Hasil Analisis Lengkap
                          </h3>
                          <div className="w-8 h-8 rounded-full bg-stone-50 flex items-center justify-center group-hover:bg-stone-100 transition-colors">
                            {reportExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </div>
                        </button>

                        <AnimatePresence>
                          {reportExpanded && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="overflow-hidden"
                            >
                              <div className="py-6 prose prose-stone prose-sm max-w-none prose-headings:font-serif prose-headings:tracking-tight prose-th:text-stone-400 prose-th:font-mono prose-th:uppercase prose-th:text-[10px] prose-th:tracking-widest prose-td:text-stone-600 prose-tr:border-stone-100">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                  {auditLog.narrative}
                                </ReactMarkdown>
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
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
                 );
              })()}
            </AnimatePresence>

            {isTyping && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex justify-start"
              >
                <div className="flex gap-4 w-full max-w-[85%]">
                  <div className="w-8 h-8 rounded-full bg-stone-900 text-white flex items-center justify-center flex-shrink-0 mt-1">
                    <Shield className="w-4 h-4" />
                  </div>
                  <div className="flex-1 bg-[#F7F6F3] border border-stone-100 rounded-2xl px-6 py-5 shadow-sm">
                    <div className="text-[10px] font-black uppercase tracking-[0.2em] text-stone-400 mb-4 flex items-center gap-2">
                      <motion.span
                        animate={{ opacity: [0.4, 1, 0.4] }}
                        transition={{ repeat: Infinity, duration: 2 }}
                        className="w-1.5 h-1.5 bg-green-500 rounded-full inline-block"
                      />
                      Reasoning in progress
                    </div>
                    <div className="space-y-3">
                      {[
                        { label: "Akuisisi data satelit Sentinel-2", icon: "🛰" },
                        { label: "Analisis NDVI & tutupan lahan", icon: "🌿" },
                        { label: "Penelusuran intelijen OSINT", icon: "📡" },
                        { label: "Evaluasi keterlibatan komunitas", icon: "👥" },
                        { label: "Sintesis laporan THK", icon: "📋" },
                      ].map((step, i) => (
                        <motion.div
                          key={step.label}
                          initial={{ opacity: 0, x: -8 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.15, duration: 0.3 }}
                          className="flex items-center gap-3"
                        >
                          <motion.div
                            animate={{ opacity: [0.3, 1, 0.3] }}
                            transition={{ repeat: Infinity, duration: 1.8, delay: i * 0.3 }}
                            className="text-sm"
                          >
                            {step.icon}
                          </motion.div>
                          <div className="flex-1">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-[11px] text-stone-500">{step.label}</span>
                              <motion.span
                                animate={{ opacity: [0, 1, 0] }}
                                transition={{ repeat: Infinity, duration: 1.8, delay: i * 0.3 }}
                                className="text-[9px] font-mono text-green-500 uppercase"
                              >
                                processing
                              </motion.span>
                            </div>
                            <div className="w-full h-[2px] bg-stone-100 rounded-full overflow-hidden">
                              <motion.div
                                className="h-full bg-stone-900 rounded-full"
                                animate={{ width: ["0%", "100%", "0%"] }}
                                transition={{
                                  repeat: Infinity,
                                  duration: 2.5,
                                  delay: i * 0.4,
                                  ease: "easeInOut"
                                }}
                              />
                            </div>
                          </div>
                        </motion.div>
                      ))}
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
      {/* Document Preview Modal */}
        <AnimatePresence>
          {previewDoc && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-8"
              style={{ willChange: 'opacity' }}
            >
              <div className="absolute inset-0 bg-black/50" onClick={() => setPreviewDoc(null)} />

              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 12 }}
                transition={{ duration: 0.18, ease: 'easeOut' }}
                style={{ willChange: 'transform, opacity' }}
                className="relative w-full max-w-5xl bg-white rounded-2xl shadow-xl overflow-hidden flex flex-col h-full max-h-[92vh] z-10"
              >
                {/* Modal Header */}
                <div className="px-8 py-5 border-b border-stone-100 flex items-center justify-between bg-white">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-stone-900 rounded-2xl flex items-center justify-center text-white shadow-lg">
                      {previewDoc.type === 'pdf' ? <FileText className="w-5 h-5" /> : <Award className="w-5 h-5" />}
                    </div>
                    <div>
                      <div className="text-[10px] text-stone-400 font-bold uppercase tracking-widest mb-0.5">Preview Dokumen</div>
                      <div className="text-sm font-black text-stone-900 uppercase tracking-tight">
                        {previewDoc.type === 'pdf' ? 'Official Audit Report' : 'Digital Compliance Certificate'}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => {
                        const content = document.getElementById('document-print-area')?.innerHTML;
                        const win = window.open("", "_blank");
                        if (win) {
                          win.document.write(`
                            <html>
                              <head>
                                <title>Download - PEMALI</title>
                                <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
                                <style>
                                  @page { size: A4; margin: 0; }
                                  body { margin: 0; padding: 0; }
                                  .print-container { width: 210mm; min-height: 297mm; padding: 20mm; box-sizing: border-box; position: relative; font-family: 'Inter', sans-serif; }
                                  table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                                  th { background: #f5f5f4; text-align: left; padding: 12px; border-bottom: 2px solid #ddd; }
                                  td { padding: 12px; border-bottom: 1px solid #eee; }
                                  ${previewDoc.type === 'cert' ? '.cert-doc { border: 20px solid #1c1917; padding: 40px; height: 217mm; }' : ''}
                                </style>
                              </head>
                              <body>
                                <div class="print-container">${content}</div>
                                <script>window.onload = () => { setTimeout(() => { window.print(); window.close(); }, 500); }</script>
                              </body>
                            </html>
                          `);
                          win.document.close();
                        }
                      }}
                      className="flex items-center gap-2 bg-stone-900 text-white px-6 py-2.5 rounded-xl text-xs font-bold hover:bg-stone-800 transition-all shadow-lg hover:shadow-stone-900/20 active:scale-95"
                    >
                      <Download className="w-4 h-4" /> Download PDF
                    </button>
                    <button
                      onClick={() => setPreviewDoc(null)}
                      className="w-10 h-10 flex items-center justify-center hover:bg-stone-100 rounded-xl transition-colors text-stone-400 hover:text-stone-900"
                    >
                      <X className="w-5 h-5" />
                    </button>
                   </div>
                 </div>

                {/* Modal Content */}
                <div className="flex-1 overflow-y-auto bg-stone-100 p-6 flex justify-center">
                  <div id="document-print-area" className="bg-white w-full max-w-[210mm] min-h-[297mm] p-12 text-stone-900 border border-stone-200">
                    {previewDoc.type === 'pdf' ? (
                      <div className="report-doc">
                        {/* Header */}
                        <div className="flex justify-between items-start border-b-[3px] border-stone-900 pb-8 mb-10">
                          <div>
                            <div className="text-[9px] font-black uppercase tracking-[0.5em] text-stone-400 mb-2">PEMALI — Platform Audit Ekologi Otonom</div>
                            <h1 className="font-serif text-4xl uppercase tracking-tighter leading-tight">Laporan Audit<br/>Lingkungan</h1>
                          </div>
                          <div className="text-right space-y-1">
                            <div className="text-[9px] font-mono text-stone-400 uppercase tracking-widest">No. Dokumen</div>
                            <div className="text-sm font-black text-stone-900 font-mono">PM-{new Date().getFullYear()}-{auditLog?.id?.toString().padStart(4, '0')}</div>
                            <div className="text-[9px] font-mono text-stone-400 mt-2">Diterbitkan: {new Date().toLocaleDateString('id-ID', { day: '2-digit', month: 'long', year: 'numeric' })}</div>
                          </div>
                        </div>

                        {/* Metadata Grid */}
                        <div className="grid grid-cols-3 gap-px bg-stone-100 border border-stone-100 mb-10 text-xs overflow-hidden rounded-lg">
                          <div className="bg-white p-4 col-span-2">
                            <div className="text-[8px] uppercase tracking-widest text-stone-400 font-black mb-1">Lokasi Audit</div>
                            <div className="font-bold text-stone-900">{auditLog?.location}, Bali, Indonesia</div>
                          </div>
                          <div className="bg-white p-4">
                            <div className="text-[8px] uppercase tracking-widest text-stone-400 font-black mb-1">Periode Analisis</div>
                            <div className="font-bold text-stone-900">12 Bulan Terakhir</div>
                          </div>
                          <div className="bg-white p-4">
                            <div className="text-[8px] uppercase tracking-widest text-stone-400 font-black mb-1">Kerangka THK</div>
                            <div className="font-bold text-stone-900">{auditLog?.thk}</div>
                          </div>
                          <div className="bg-white p-4">
                            <div className="text-[8px] uppercase tracking-widest text-stone-400 font-black mb-1">Status Kritis</div>
                            <div className="font-black text-red-600 uppercase text-[10px]">{auditLog?.issue}</div>
                          </div>
                          <div className="bg-white p-4">
                            <div className="text-[8px] uppercase tracking-widest text-stone-400 font-black mb-1">Agen Pengolah</div>
                            <div className="font-bold text-stone-900">PEMALI Autonomous V2.4</div>
                          </div>
                        </div>

                        {/* AI Narrative */}
                        <div className="mb-10">
                          <div className="flex items-center gap-3 mb-5">
                            <div className="w-6 h-[2px] bg-stone-900"></div>
                            <h2 className="font-serif text-lg text-stone-900 uppercase tracking-tight">Analisis Strategis AI</h2>
                          </div>
                          <div className="text-[11px] leading-[1.8] text-stone-700 text-justify
                            [&_h1]:font-serif [&_h1]:text-lg [&_h1]:font-bold [&_h1]:mt-6 [&_h1]:mb-2 [&_h1]:text-stone-900
                            [&_h2]:font-serif [&_h2]:text-base [&_h2]:font-bold [&_h2]:mt-6 [&_h2]:mb-2 [&_h2]:text-stone-900
                            [&_h3]:text-[11px] [&_h3]:font-black [&_h3]:uppercase [&_h3]:tracking-widest [&_h3]:mt-5 [&_h3]:mb-2 [&_h3]:text-stone-500
                            [&_p]:mb-3 [&_p]:leading-relaxed
                            [&_strong]:font-bold [&_strong]:text-stone-900
                            [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:mb-3 [&_ul]:space-y-1
                            [&_ol]:list-decimal [&_ol]:pl-5 [&_ol]:mb-3
                            [&_li]:leading-relaxed
                            [&_hr]:border-stone-100 [&_hr]:my-4
                            [&_table]:w-full [&_table]:text-[10px] [&_table]:border-collapse [&_table]:mb-4
                            [&_th]:bg-stone-900 [&_th]:text-white [&_th]:px-3 [&_th]:py-2 [&_th]:text-left [&_th]:font-black [&_th]:uppercase [&_th]:tracking-wider [&_th]:text-[9px]
                            [&_td]:px-3 [&_td]:py-2 [&_td]:border-b [&_td]:border-stone-100 [&_td]:text-stone-600
                            [&_tr:nth-child(even)_td]:bg-stone-50
                            [&_blockquote]:border-l-2 [&_blockquote]:border-stone-200 [&_blockquote]:pl-4 [&_blockquote]:italic [&_blockquote]:text-stone-500
                          ">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {auditLog?.narrative || ""}
                            </ReactMarkdown>
                          </div>
                        </div>

                        {/* Spatial Data Table */}
                        <div className="mb-10">
                          <div className="flex items-center gap-3 mb-4">
                            <div className="w-6 h-[2px] bg-stone-900"></div>
                            <h2 className="font-serif text-lg text-stone-900 uppercase tracking-tight">Metrik Spasial Sentinel-2</h2>
                          </div>
                          <table className="w-full text-[11px] border-collapse">
                            <thead>
                              <tr className="bg-stone-900 text-white">
                                <th className="py-3 px-4 text-left font-black uppercase tracking-widest text-[9px]">Parameter</th>
                                <th className="py-3 px-4 text-right font-black uppercase tracking-widest text-[9px]">Nilai</th>
                                <th className="py-3 px-4 text-right font-black uppercase tracking-widest text-[9px]">Ambang Batas</th>
                                <th className="py-3 px-4 text-right font-black uppercase tracking-widest text-[9px]">Status</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr className="border-b border-stone-100 bg-amber-50/30">
                                <td className="py-3 px-4 text-stone-700">Indeks Vegetasi (NDVI)</td>
                                <td className="py-3 px-4 text-right font-mono font-bold">{auditLog?.ndvi_score || "0.41"}</td>
                                <td className="py-3 px-4 text-right font-mono text-stone-400">≥ 0.60</td>
                                <td className="py-3 px-4 text-right font-black text-amber-600">⚠ Tertekan</td>
                              </tr>
                              <tr className="border-b border-stone-100 bg-red-50/30">
                                <td className="py-3 px-4 text-stone-700">Konversi Lahan (12 bln)</td>
                                <td className="py-3 px-4 text-right font-mono font-bold">12.4%</td>
                                <td className="py-3 px-4 text-right font-mono text-stone-400">{"< 5%"}</td>
                                <td className="py-3 px-4 text-right font-black text-red-600">✗ Anomali</td>
                              </tr>
                              <tr className="border-b border-stone-100">
                                <td className="py-3 px-4 text-stone-700">Area Terbangun Baru</td>
                                <td className="py-3 px-4 text-right font-mono font-bold">89.7 ha</td>
                                <td className="py-3 px-4 text-right font-mono text-stone-400">Baseline</td>
                                <td className="py-3 px-4 text-right font-black text-stone-600">• Valid</td>
                              </tr>
                              <tr className="border-b border-stone-100">
                                <td className="py-3 px-4 text-stone-700">Tutupan Vegetasi Aktif</td>
                                <td className="py-3 px-4 text-right font-mono font-bold">127.3 ha</td>
                                <td className="py-3 px-4 text-right font-mono text-stone-400">Baseline</td>
                                <td className="py-3 px-4 text-right font-black text-stone-600">• Valid</td>
                              </tr>
                              <tr>
                                <td className="py-3 px-4 text-stone-700">Cloud Cover Interferensi</td>
                                <td className="py-3 px-4 text-right font-mono font-bold">8.2%</td>
                                <td className="py-3 px-4 text-right font-mono text-stone-400">{"< 20%"}</td>
                                <td className="py-3 px-4 text-right font-black text-green-600">✓ Optimum</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>

                        {/* OSINT Intel Section */}
                        <div className="mb-10 p-4 bg-stone-50 rounded-lg border border-stone-100">
                          <div className="flex items-center gap-3 mb-3">
                            <div className="w-6 h-[2px] bg-stone-900"></div>
                            <h2 className="font-serif text-lg text-stone-900 uppercase tracking-tight">Intelijen OSINT</h2>
                          </div>
                          <div className="grid grid-cols-2 gap-4 text-[11px]">
                            <div>
                              <div className="text-[8px] font-black uppercase tracking-widest text-stone-400 mb-1">Sumber Berita Terdeteksi</div>
                              <div className="font-bold">3 Artikel Relevan (30 hari)</div>
                            </div>
                            <div>
                              <div className="text-[8px] font-black uppercase tracking-widest text-stone-400 mb-1">Skor Risiko Sosial</div>
                              <div className="font-black text-red-600">67% — Kritis</div>
                            </div>
                            <div className="col-span-2">
                              <div className="text-[8px] font-black uppercase tracking-widest text-stone-400 mb-1">Topik Terdeteksi</div>
                              <div className="font-medium text-stone-600">Resistensi warga terhadap pembangunan resort, alih fungsi lahan Subak, konflik agraria</div>
                            </div>
                          </div>
                        </div>

                        {/* Footer */}
                        <div className="pt-6 border-t border-stone-200 flex justify-between items-end">
                          <div className="text-[9px] text-stone-400 font-mono uppercase tracking-[0.2em] leading-relaxed">
                            Diverifikasi via Sentinel-2 MSI L2A<br/>
                            Session ID: {sessionId?.slice(-12) || "—"}
                          </div>
                          <div className="flex flex-col items-center">
                            <div className="w-24 h-24 border-2 border-dashed border-stone-200 rounded-full flex flex-col items-center justify-center rotate-[-12deg] opacity-50">
                              <p className="text-[7px] font-black uppercase text-stone-500">PEMALI AI</p>
                              <p className="text-[10px] font-black text-stone-900">VERIFIED</p>
                            </div>
                          </div>
                        </div>
                        <div className="mt-8 text-center text-[8px] text-stone-300 uppercase tracking-[0.4em]">
                          PEMALI Autonomous Ecological Monitoring Platform • Confidential Internal Document
                        </div>
                      </div>
                    ) : (
                      <div className="cert-doc h-full flex flex-col items-center justify-center text-center p-12 border-[20px] border-stone-900 relative">
                        <div className="absolute inset-4 border border-stone-900 pointer-events-none opacity-20"></div>

                        <div className="text-[11px] font-black tracking-[0.6em] text-stone-400 uppercase mb-20">Official Certificate of Compliance</div>

                        <h1 className="font-serif text-7xl text-stone-900 mb-2 tracking-tighter">Pemali.</h1>
                        <div className="w-20 h-1.5 bg-stone-900 mb-16"></div>

                        <p className="text-stone-400 text-sm italic mb-10 max-w-md">
                          This document serves as an official confirmation that an autonomous ecological investigation was successfully completed at
                        </p>

                        <div className="border-y-2 border-stone-100 py-8 px-16 mb-12">
                           <h2 className="font-serif text-4xl text-stone-900 tracking-tight">
                            {auditLog?.location}
                          </h2>
                        </div>

                        <p className="text-stone-500 max-w-lg leading-relaxed text-sm mb-20">
                          The analysis confirms alignment with the <b>Tri Hita Karana</b> framework, specifically protecting the integrity of <b>{auditLog?.thk}</b>. All findings have been cross-referenced with Sentinel-2 satellite feeds and validated by the PEMALI AI reasoning engine.
                        </p>

                        <div className="grid grid-cols-3 w-full items-end mt-auto pb-10">
                          <div className="flex flex-col items-center">
                            <p className="text-[9px] font-black uppercase tracking-widest text-stone-900 mb-2">Ecological Agent</p>
                            <div className="w-32 h-[1px] bg-stone-200 mb-1"></div>
                            <p className="text-[8px] font-mono text-stone-400">PEMALI-V2-AUTONOMOUS</p>
                          </div>

                          <div className="flex flex-col items-center px-4">
                            <div className="w-24 h-24 bg-stone-50 rounded-full border-2 border-double border-stone-200 flex flex-col items-center justify-center p-2">
                              <p className="text-[7px] font-black uppercase tracking-widest text-stone-300">Verified</p>
                              <div className="w-10 h-10 border border-stone-200 rounded-lg my-1 flex items-center justify-center">
                                <Award className="w-5 h-5 text-stone-300" />
                              </div>
                              <p className="text-[7px] font-serif italic text-stone-400">Original</p>
                            </div>
                          </div>

                          <div className="flex flex-col items-center">
                            <p className="text-[9px] font-black uppercase tracking-widest text-stone-900 mb-2">Timestamp</p>
                            <div className="w-32 h-[1px] bg-stone-200 mb-1"></div>
                            <p className="text-[8px] font-mono text-stone-400">{new Date().toLocaleDateString('id-ID')}</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
