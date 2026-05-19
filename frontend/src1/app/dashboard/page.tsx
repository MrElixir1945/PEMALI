"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sidebar,
  AgentArea,
  FinalReport,
} from "@/components/pemali/dashboard/ObservationZone";
import {
  ChatMessages,
  ChatInput,
} from "@/components/pemali/dashboard/InteractionZone";

import {
  type TelemetryEvent,
  type Session,
  type ChatMessage as Message,
} from "@/lib/dashboard";

// ── Typing Bubble ──────────────────────────────────────
function TypingBubble() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      className="flex items-end gap-3 mb-4"
    >
      <div className="w-7 h-7 rounded-full bg-[var(--pemali-accent)]/10 border border-[var(--pemali-border)] flex items-center justify-center shrink-0">
        <div className="w-1.5 h-1.5 rounded-full bg-[var(--pemali-accent)]" />
      </div>
      <div className="bg-[var(--pemali-surface)] border border-[var(--pemali-border)] rounded-2xl rounded-bl-sm px-4 py-3">
        <div className="flex gap-1 items-center h-4">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-[var(--pemali-text-muted)]"
              animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
              transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
}

// ── Welcome Screen ─────────────────────────────────────
function WelcomeScreen({ onSend }: { onSend: (msg: string) => void }) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [greeting, setGreeting] = useState({ text: "Selamat Datang", sub: "Mulai hari dengan memantau kondisi lingkungan Bali.", icon: "🌿" });

  useEffect(() => {
    const calc = () => {
      const h = new Date().getHours();
      if (h >= 5 && h < 12) return { text: "Selamat Pagi", sub: "Mulai hari dengan memantau kondisi lingkungan Bali.", icon: "☀️" };
      if (h >= 12 && h < 15) return { text: "Selamat Siang", sub: "Pantau kondisi lingkungan Bali siang ini.", icon: "🌤️" };
      if (h >= 15 && h < 19) return { text: "Selamat Sore", sub: "Perbarui data audit sore ini.", icon: "🌅" };
      return { text: "Selamat Malam", sub: "Pemantauan tetap berjalan malam ini.", icon: "🌙" };
    };
    setGreeting(calc());
    const t = setInterval(() => setGreeting(calc()), 60000);
    return () => clearInterval(t);
  }, []);

  const SUGGESTIONS = [
    "Audit vegetasi Ubud",
    "Cek kualitas air Sungai Ayung",
    "Analisis polusi udara Denpasar",
    "Deteksi hotspot kebakaran Kintamani",
  ];

  const handleSend = () => {
    const v = value.trim();
    if (!v) return;
    onSend(v);
    setValue("");
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.25, 0.1, 0.25, 1] }}
      className="w-full max-w-2xl flex flex-col items-center gap-8"
    >
      <div className="text-4xl">{greeting.icon}</div>
      <div className="text-center">
        <h1 className="text-4xl font-medium mb-2 tracking-tight" style={{ fontFamily: "'Lora', serif" }}>
          {greeting.text}
        </h1>
        <p className="text-[var(--pemali-text-secondary)] text-base">{greeting.sub}</p>
      </div>

      <div className="w-full bg-[var(--pemali-surface)] border border-[var(--pemali-border)] rounded-2xl p-4 focus-within:border-[var(--pemali-border-glow)] transition-all duration-300" style={{ boxShadow: "0 4px 24px rgba(0,0,0,0.06)" }}>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
          placeholder="Apa yang bisa saya bantu hari ini?"
          className="w-full bg-transparent text-[var(--pemali-text-primary)] placeholder-[var(--pemali-text-muted)] text-sm resize-none outline-none min-h-[60px] max-h-[200px]"
          rows={2}
        />
        <div className="flex items-center justify-between mt-2 pt-2 border-t border-[var(--pemali-border)]">
          <span className="text-[11px] text-[var(--pemali-text-muted)]">Enter kirim · Shift+Enter baris baru</span>
          <button
            onClick={handleSend}
            disabled={!value.trim()}
            className="w-8 h-8 rounded-full bg-[var(--pemali-accent)] flex items-center justify-center disabled:opacity-30 hover:opacity-90 transition-opacity"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5"><path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"/></svg>
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 justify-center">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSend(s)}
            className="px-3 py-1.5 text-[12px] border border-[var(--pemali-border)] rounded-full text-[var(--pemali-text-secondary)] hover:text-[var(--pemali-text-primary)] hover:border-[var(--pemali-border-glow)] transition-all"
          >
            {s}
          </button>
        ))}
      </div>
    </motion.div>
  );
}

// ── Main Dashboard ─────────────────────────────────────
export default function PemaliDashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [finalReport, setFinalReport] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [auditMode, setAuditMode] = useState(false);
  const [observationView, setObservationView] = useState("process");
  const chatEndRef = useRef<HTMLDivElement>(null);

  const currentModel = process.env.NEXT_PUBLIC_OPENROUTER_MODEL || "DEEPSEEK-R1";
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const loadSessions = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/api/sessions`);
      if (res.ok) setSessions(await res.json());
    } catch (err) { console.error("Sessions:", err); }
  }, [backendUrl]);

  useEffect(() => { loadSessions(); }, [loadSessions]);

  // Auto-refresh session list setiap 3 detik
  useEffect(() => {
    const interval = setInterval(loadSessions, 3000);
    return () => clearInterval(interval);
  }, [loadSessions]);

  // SSE Monitor — langsung ke backend, bukan proxy
  useEffect(() => {
    const es = new EventSource(`${backendUrl}/api/telemetry`);
    
    es.onopen = () => {
      console.log("[SSE] Connected to backend telemetry");
      setIsConnected(true);
    };
    
    es.onerror = (err) => {
      console.error("[SSE] Connection error:", err);
      setIsConnected(false);
    };

    es.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        console.debug("[SSE] Event received:", event);
        setIsConnected(true);

        // Ping ignored
        if (event.type === "ping") return;

        // Sub-agent aktif ATAU Manager mulai planning → masuk audit mode
        if (
          (event.node_id && event.node_id !== "manager" && event.node_id !== "system") ||
          (event.node_id === "manager" && event.metadata?.phase === "planning")
        ) {
          setAuditMode(true);
        }

        // Synthesis selesai → auto-switch ke laporan
        if (event.node_id === "synthesis" && event.state === "DONE" && event.narrative) {
          setFinalReport(event.narrative);
          setObservationView("report");
          setIsTyping(false);
          setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last?.content.includes("Audit Selesai")) return prev;
            return [...prev, { 
              role: "assistant", 
              content: "✅ **Audit Selesai.** Laporan lengkap telah kami susun dan tampilkan di panel tengah. Silakan tinjau temuan kami.", 
              ts: Date.now() 
            }];
          });
        }

        // Manager selesai (chat biasa tanpa sub-agent) → stop typing, simpan reply
        // Skip untuk final_report karena sudah dihandle oleh synthesis DONE
        if (event.node_id === "manager" && event.state === "DONE" && event.narrative && event.metadata?.type !== "final_report") {
          setIsTyping(false);
          setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last?.role === "assistant" && last.content === event.narrative) return prev;
            return [...prev, { role: "assistant", content: event.narrative, ts: Date.now() }];
          });
        }

        setEvents(prev => [...prev.slice(-199), event]);
      } catch (err) {
        console.warn("[SSE] Parse error:", err, e.data);
      }
    };

    return () => es.close();
  }, [backendUrl]);

  const handleSelectSession = async (id: string) => {
    setActiveSessionId(id);
    setIsTyping(false);
    setEvents([]);
    setFinalReport(null);
    setAuditMode(false);
    setObservationView("process");

    try {
      const res = await fetch(`${backendUrl}/api/history/${id}`);
      if (!res.ok) throw new Error("Gagal mengambil histori");
      const data = await res.json();
      
      setActiveSessionId(id);
      setHasStarted(true);
      
      // 1. Rekonstruksi Telemetry dari memory untuk DAG (Logic Thinking)
      const reconstructedEvents: any[] = (data.agent_memories || [])
        .filter((m: any) => m.role === "assistant")
        .map((m: any) => {
          let node_id = "manager";
          const content = m.content.toLowerCase();
          
          if (content.includes("geo_agent") || content.includes("ndvi") || content.includes("satelit")) node_id = "geo_agent";
          else if (content.includes("water_agent") || content.includes("kualitas air") || content.includes("ph ") || content.includes("sungai") || content.includes("danau") || content.includes(" air ") || content.includes("hidrologi")) node_id = "water_agent";
          else if (content.includes("fire_agent") || content.includes("thermal") || content.includes("kebakaran") || content.includes("hotspot")) node_id = "fire_agent";
          else if (content.includes("osint_agent") || content.includes("berita") || content.includes("media") || content.includes("sentimen")) node_id = "osint_agent";
          else if (content.includes("scheduler_agent") || content.includes("jadwal") || content.includes("otomatis") || content.includes("rutin")) node_id = "scheduler_agent";
          else if (m.content.includes("# Laporan") || m.content.includes("# 🌿") || content.includes("audit selesai")) node_id = "synthesis";

          return {
            node_id,
            state: "DONE",
            narrative: m.content.split("\n")[0].substring(0, 150) + "...", 
            type: "node_state",
            timestamp: new Date(m.created_at).getTime()
          };
        });
      setEvents(reconstructedEvents);

      // 2. Filter pesan untuk chat UI (Editorial Look)
      const chatHistory = (data.agent_memories || [])
        .filter((m: any) => {
          if (m.role === "user") return true;
          if (m.role === "assistant") {
            const trimmed = m.content.trim();
            const isJson = trimmed.startsWith("{") && trimmed.endsWith("}");
            if (isJson) {
              try {
                const parsed = JSON.parse(trimmed);
                // Sembunyikan jika ini data teknis murni (status success/error)
                if (parsed.status && (parsed.status === "success" || parsed.status === "error")) return false;
                // Sembunyikan jika ini tool call internal
                if (parsed.tool_calls || parsed.action) return false;
              } catch (e) {
                // Jika gagal parse, berarti ini narasi biasa yang kebetulan diawali {
                return true;
              }
            }
            return true;
          }
          return false;
        })
        .map((m: any) => ({
          role: m.role as any,
          content: m.content,
          ts: new Date(m.created_at).getTime()
        }));
      setMessages(chatHistory);

      // 3. Cari laporan di audit_logs
      const report = (data.audit_logs || []).find(
        (l: any) => l.narrative_report && (l.narrative_report.includes("#") || l.narrative_report.includes("🌿"))
      );
      
      if (report) {
        setFinalReport(report.narrative_report);
        setAuditMode(true);
        setObservationView("report");
      } else {
        // Fallback: cari laporan di memory
        const reportInMemory = (data.agent_memories || [])
          .reverse()
          .find((m: any) => m.role === "assistant" && (m.content.includes("# Laporan") || m.content.includes("# 🌿")));
        
        if (reportInMemory) {
          setFinalReport(reportInMemory.content);
          setAuditMode(true);
          setObservationView("report");
        } else {
          setFinalReport(null);
          setAuditMode(false);
          setObservationView("process");
        }
      }
    } catch (err) {
      console.error("Error loading history:", err);
    }
  };

  const handleNewAudit = () => {
    setActiveSessionId(null);
    setMessages([]);
    setEvents([]);
    setFinalReport(null);
    setObservationView("process");
    setIsTyping(false);
    setAuditMode(false);
    setHasStarted(false);
  };

  const handleSendMessage = async (content: string) => {
    setHasStarted(true);
    setMessages(prev => [...prev, { role: "user", content, ts: Date.now() }]);
    setIsTyping(true);
    setEvents([]);

    try {
      const res = await fetch(`${backendUrl}/api/trigger`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: content, session_id: activeSessionId })
      });
      if (res.ok) {
        const data = await res.json();
        if (!activeSessionId) { setActiveSessionId(data.session_id); loadSessions(); }
      } else setIsTyping(false);
    } catch { setIsTyping(false); }
  };

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const initialPrompt = params.get("prompt");
      if (initialPrompt) {
        window.history.replaceState({}, document.title, window.location.pathname);
        handleSendMessage(initialPrompt);
      }
    }
  }, []);


  return (
    <main className="h-screen w-full bg-[var(--pemali-bg)] flex overflow-hidden font-sans text-[var(--pemali-text-primary)]">
      {/* ── Sidebar ── */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            key="sidebar"
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 280, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
            className="h-full shrink-0 overflow-hidden"
          >
            <Sidebar
              isOpen={sidebarOpen}
              onToggle={() => setSidebarOpen(false)}
              activeSessionId={activeSessionId || ""}
              sessions={sessions}
              onSelectSession={handleSelectSession}
              onNewAudit={handleNewAudit}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Main ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Status Bar */}
        <div className="h-10 border-b border-[var(--pemali-border)] bg-[var(--pemali-surface)]/80 backdrop-blur-md flex items-center justify-between px-4 shrink-0">
          <div className="flex items-center gap-5">
            {!sidebarOpen && (
              <button onClick={() => setSidebarOpen(true)} className="p-1 rounded text-[var(--pemali-text-muted)] hover:text-[var(--pemali-text-primary)] transition-colors">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/></svg>
              </button>
            )}
            <div className="flex items-center gap-2">
              <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-[var(--state-executing)] animate-pulse' : 'bg-[var(--state-error)]'}`} />
              <span className="text-[10px] text-[var(--pemali-text-muted)] font-mono uppercase tracking-wider">Model: {currentModel}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-[var(--state-complete)]' : 'bg-[var(--state-error)]'}`} />
              <span className="text-[10px] text-[var(--pemali-text-muted)] font-mono uppercase tracking-wider">
                {isConnected ? 'Worker Standby' : 'Worker Offline'}
              </span>
            </div>
          </div>
          {/* Tab control hanya muncul di audit mode */}
          <div className="flex items-center gap-3">
            {auditMode && hasStarted && (
              <>
                <div className="flex gap-1 bg-[var(--pemali-bg)] px-1 py-0.5 rounded-md border border-[var(--pemali-border)]">
                  <button onClick={() => setObservationView("process")} className={`px-2.5 py-0.5 text-[10px] font-medium rounded transition-all ${observationView === "process" ? "bg-[var(--pemali-accent)] text-white" : "text-[var(--pemali-text-secondary)] hover:text-[var(--pemali-text-primary)]"}`}>
                    Alur Kerja
                  </button>
                  <button onClick={() => setObservationView("report")} className={`px-2.5 py-0.5 text-[10px] font-medium rounded transition-all ${observationView === "report" ? "bg-[var(--pemali-accent)] text-white" : "text-[var(--pemali-text-secondary)] hover:text-[var(--pemali-text-primary)]"}`}>
                    Laporan Final
                  </button>
                </div>
                <button onClick={() => setAuditMode(false)} className="text-[10px] text-[var(--pemali-text-muted)] hover:text-[var(--pemali-text-primary)] font-mono uppercase tracking-wider transition-colors">
                  ← Chat
                </button>
              </>
            )}
            <span className="text-[9px] text-[var(--pemali-text-muted)] font-mono uppercase opacity-40">Geo-Audit v2.0</span>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          <AnimatePresence mode="wait">
            {auditMode && hasStarted ? (
              /* ── AUDIT MODE: Split-pane ── */
              <motion.div key="audit" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex overflow-hidden">
                {/* Kiri: DAG / Laporan */}
                <div className="flex-[1.6] border-r border-[var(--pemali-border)] flex flex-col overflow-hidden">
                  <div className="flex-1 overflow-y-auto p-6 scrollbar-none">
                    {observationView === "process"
                      ? <AgentArea events={events} />
                      : <FinalReport content={finalReport || ""} isLoading={false} />
                    }
                  </div>
                </div>

                {/* Kanan: Chat */}
                <div className="flex-1 flex flex-col overflow-hidden bg-[var(--pemali-surface)]/10">
                  <div className="flex-1 overflow-y-auto px-6 pt-6 pb-2 scrollbar-none">
                    <ChatMessages 
                      messages={messages} 
                      onOpenReport={() => {
                        setAuditMode(true);
                        setObservationView("report");
                      }}
                    />
                    <AnimatePresence>{isTyping && <TypingBubble />}</AnimatePresence>
                    <div ref={chatEndRef} />
                  </div>
                  <div className="px-6 py-4 border-t border-[var(--pemali-border)] shrink-0">
                    <ChatInput onSend={handleSendMessage} disabled={isTyping} />
                  </div>
                </div>
              </motion.div>
            ) : (
              /* ── CHAT MODE: Full-width ── */
              <motion.div key="chat" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col overflow-hidden">
                {hasStarted ? (
                  <>
                    <div className="flex-1 overflow-y-auto scrollbar-none">
                      <div className="max-w-3xl mx-auto px-6 pt-8 pb-4">
                        <ChatMessages 
                          messages={messages} 
                          onOpenReport={() => {
                            setAuditMode(true);
                            setObservationView("report");
                          }}
                        />
                        <AnimatePresence>{isTyping && <TypingBubble />}</AnimatePresence>
                        <div ref={chatEndRef} />
                      </div>
                    </div>

                    <div className="border-t border-[var(--pemali-border)] bg-[var(--pemali-bg)]/50 backdrop-blur-sm shrink-0">
                      {/* Tombol kembali ke audit mode kalau ada laporan */}
                      {finalReport && (
                        <div className="max-w-3xl mx-auto px-6 pt-3">
                          <button
                            onClick={() => setAuditMode(true)}
                            className="w-full py-2 rounded-lg border border-[var(--pemali-border-glow)] text-[11px] text-[var(--pemali-accent)] font-medium hover:bg-[var(--pemali-accent)]/5 transition-all flex items-center justify-center gap-2"
                          >
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12l9-9 9 9"/><path d="M9 21V9h6v12"/></svg>
                            Lihat Alur Kerja & Laporan Audit
                          </button>
                        </div>
                      )}
                      <div className="max-w-3xl mx-auto px-6 py-4">
                        <ChatInput onSend={handleSendMessage} disabled={isTyping} />
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex flex-col items-center justify-center px-6">
                    <WelcomeScreen onSend={handleSendMessage} />
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </main>
  );
}
