"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { Sidebar, FinalReport } from "@/components/pemali/dashboard/ObservationZone";
import {
  ChatMessages,
  ChatInput,
} from "@/components/pemali/dashboard/InteractionZone";

import {
  type TelemetryEvent,
  type Session,
  type ChatMessage as Message,
} from "@/lib/dashboard";
import { useTelemetryStore } from "@/stores/telemetryStore";
import { Cpu, Database, Activity, PanelLeft, Plus, Search, MessageSquare, Leaf, Waves, Wind, Flame, Home, Brain, Globe, Droplets, ChevronDown, ChevronUp, Check, AlertCircle, Calendar, FileText } from "lucide-react";

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

// ── Agent Metadata & Icons mapping (no emoji) ───────────
const AGENT_META: Record<string, { name: string; subtitle: string; icon: React.ComponentType<any> }> = {
  manager: {
    name: "Manager Agent",
    subtitle: "STRATEGIC PLANNING",
    icon: Brain,
  },
  geo_agent: {
    name: "Geo Agent",
    subtitle: "SATELLITE AUDIT (NDVI)",
    icon: Globe,
  },
  water_agent: {
    name: "Water Agent",
    subtitle: "WATER SENSOR AUDIT",
    icon: Droplets,
  },
  fire_agent: {
    name: "Fire Agent",
    subtitle: "THERMAL AUDIT (HOTSPOTS)",
    icon: Flame,
  },
  osint_agent: {
    name: "OSINT Agent",
    subtitle: "PUBLIC DATA SOURCE AUDIT",
    icon: Search,
  },
  scheduler_agent: {
    name: "Scheduler Agent",
    subtitle: "AUTONOMOUS TICK LOOP",
    icon: Calendar,
  },
  synthesis: {
    name: "Synthesis Agent",
    subtitle: "FINAL RECOMMENDATIONS",
    icon: FileText,
  },
};

const getAgentMeta = (nodeId: string) => {
  return AGENT_META[nodeId] || {
    name: nodeId.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()) + " Agent",
    subtitle: "COGNITIVE SUB-AGENT",
    icon: Brain,
  };
};

interface NodeData {
  node_id: string;
  state: string;
  narrative: string;
  node_type: string;
  tool_name?: string;
}

// ── AgentThinkingCard (collapsible with typewriter) ───
function AgentThinkingCard({
  node,
  isActive,
  isDone,
  isError,
  isOpen,
  onToggle,
}: {
  node: NodeData;
  isActive: boolean;
  isDone: boolean;
  isError: boolean;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const meta = getAgentMeta(node.node_id);
  const Icon = meta.icon;

  const [typedText, setTypedText] = useState("");
  
  // Typewriter effect (15ms/character) — skip if already done (history mode)
  useEffect(() => {
    const text = node.narrative || "";
    const done = node.state === "DONE" || node.state === "ERROR";
    if (done) {
      setTypedText(text);
      return;
    }
    setTypedText("");
    if (!text) return;

    let index = 0;
    let timer: NodeJS.Timeout;
    const tick = () => {
      index++;
      setTypedText(text.slice(0, index));
      if (index < text.length) timer = setTimeout(tick, 15);
    };
    tick();
    return () => clearTimeout(timer);
  }, [node.narrative]);

  const isTyping = isActive && typedText.length < (node.narrative || "").length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="w-full bg-[#faf9f6] rounded-lg border overflow-hidden"
      style={{
        borderColor: isDone ? "#10B981" : isError ? "#EF4444" : "#e5e2dc",
        boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
        transition: "border-color 500ms ease, background-color 500ms ease",
      }}
    >
      {/* Header Row */}
      <div 
        onClick={onToggle}
        className="px-5 py-4 flex items-center justify-between cursor-pointer select-none hover:bg-black/[0.01] transition-colors"
      >
        <div className="flex items-center gap-4">
          <div 
            className="w-10 h-10 rounded-lg flex items-center justify-center border"
            style={{
              borderColor: isDone ? "#d1fae5" : isError ? "#fee2e2" : "#e5e2dc",
              backgroundColor: isDone ? "#f0fdf4" : isError ? "#fef2f2" : "#ffffff",
              color: isDone ? "#059669" : isError ? "#dc2626" : "#7a7670",
              transition: "all 500ms ease",
            }}
          >
            <Icon size={20} />
          </div>
          <div>
            <h4 className="text-[14px] font-bold text-[#1A1916] leading-none mb-1.5">
              {meta.name}
            </h4>
            <p className="text-[9px] font-mono tracking-widest text-[#999] uppercase leading-none">
              {meta.subtitle}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Badge */}
          {isDone ? (
            <span className="flex items-center gap-1 text-[10px] font-bold text-[#047857] bg-[#d1fae5] px-2.5 py-1 rounded-full uppercase tracking-wider font-mono">
              <Check size={11} strokeWidth={3} />
              Selesai
            </span>
          ) : isError ? (
            <span className="flex items-center gap-1 text-[10px] font-bold text-[#b91c1c] bg-[#fee2e2] px-2.5 py-1 rounded-full uppercase tracking-wider font-mono">
              <AlertCircle size={11} strokeWidth={3} />
              Error
            </span>
          ) : (
            <span className="flex items-center gap-2 text-[10px] font-bold text-[#d97706] bg-[#fef3c7] px-2.5 py-1 rounded-full uppercase tracking-wider font-mono">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#d97706] opacity-75"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-[#d97706]"></span>
              </span>
              Memproses
            </span>
          )}

          {/* Chevron Collapsible Trigger */}
          {isOpen ? (
            <ChevronUp size={16} className="text-[#999]" />
          ) : (
            <ChevronDown size={16} className="text-[#999]" />
          )}
        </div>
      </div>

      {/* Narrative Monospace Log */}
      <AnimatePresence initial={false}>
        {isOpen && (node.narrative || isTyping) && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="border-t border-[#e5e2dc] bg-black/[0.01]"
          >
            <div className="px-5 py-4 font-mono text-[11px] text-[#7A7670] leading-relaxed whitespace-pre-wrap">
              {typedText || "Menunggu proses..."}
              {isTyping && (
                <span className="inline-block animate-pulse font-sans font-bold text-[var(--pemali-accent)] ml-0.5">▌</span>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── DagVisualizer Redesigned (Card Sequential Stack) ───
function DagVisualizer({
  events,
  finalReport,
  messages,
  view,
  onToggleView,
}: {
  events: TelemetryEvent[];
  finalReport: string | null;
  messages: Message[];
  view: string;
  onToggleView: () => void;
}) {
  // Build node map in order of appearance
  const nodeMap = new Map<string, NodeData>();
  for (const ev of events) {
    if (!ev.node_id || ev.node_id === "system") continue;
    const prev = nodeMap.get(ev.node_id);
    nodeMap.set(ev.node_id, {
      node_id: ev.node_id,
      state: ev.state,
      narrative: ev.narrative || prev?.narrative || "",
      node_type: (ev as any).node_type || prev?.node_type || "",
      tool_name: (ev as any).metadata?.tool_name || prev?.tool_name,
    });
  }

  const allNodes = [...nodeMap.values()];

  // Status counts
  const doneCount    = allNodes.filter(n => n.state === "DONE").length;
  const runningCount = allNodes.filter(n => ["EXECUTING","THINKING","SPAWNING"].includes(n.state)).length;
  const waitingCount = Math.max(0, allNodes.length - doneCount - runningCount);

  // Fallback to last assistant report content
  const lastAssistantMsg = [...messages].reverse().find(
    m => m.role === "assistant" && !m.content.includes("Audit Selesai")
  )?.content || "";
  const reportContent = finalReport || lastAssistantMsg;

  // React state Map to track manual overrides by the user
  const [manualExpanded, setManualExpanded] = useState<Map<string, boolean>>(new Map());

  // Determine if a card should be open
  const isOpen = (nodeId: string, state: string) => {
    if (manualExpanded.has(nodeId)) {
      return manualExpanded.get(nodeId)!;
    }
    // Default: open if actively thinking/executing/spawning
    return ["THINKING", "EXECUTING", "SPAWNING"].includes(state);
  };

  const handleToggleCard = (nodeId: string, currentState: string) => {
    setManualExpanded(prev => {
      const copy = new Map(prev);
      const currentOpen = isOpen(nodeId, currentState);
      copy.set(nodeId, !currentOpen);
      return copy;
    });
  };

  return (
    <div
      className="h-full flex flex-col bg-white overflow-hidden"
      style={{ borderRight: "1px solid #e5e2dc" }}
    >
      {/* Header */}
      <div className="px-6 pt-5 pb-2 shrink-0 flex items-center justify-between">
        <span className="text-[10px] font-mono font-semibold tracking-[0.15em] text-[#999] uppercase">
          {view === "report" ? "Laporan Audit" : "Alur Kerja"}
        </span>
        {view === "report" && (
          <button
            onClick={onToggleView}
            className="text-[10px] font-mono text-[#7A7670] hover:text-[#1A1916] transition-colors"
          >
            ← Lihat Alur Kerja
          </button>
        )}
      </div>

      {/* Status summary bar */}
      {view === "dag" && allNodes.length > 0 && (
        <div className="px-6 pb-3 shrink-0">
          <p className="text-[10px] font-mono text-[#999]">
            <span style={{ color: "#166534" }}>{doneCount} selesai</span>
            {" · "}
            <span style={{ color: "#d97706" }}>{runningCount} berjalan</span>
            {" · "}
            <span>{waitingCount} menunggu</span>
          </p>
        </div>
      )}

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-6 pb-6 scrollbar-none">
        {view === "report" ? (
          /* ── Report View ── */
          reportContent ? (
            <FinalReport content={reportContent} isLoading={false} />
          ) : (
            <p className="text-[12px] text-[#999] mt-4">Laporan belum tersedia.</p>
          )
        ) : events.length === 0 ? (
          /* ── Empty ── */
          <div className="flex flex-col items-center justify-center h-48 gap-3">
            <motion.div
              className="w-2 h-2 rounded-full bg-[#ccc]"
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.6, repeat: Infinity }}
            />
            <p className="text-[12px] text-[#999]">Menunggu respons agent...</p>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {allNodes.map(node => (
              <AgentThinkingCard
                key={node.node_id}
                node={node}
                isActive={["EXECUTING", "THINKING", "SPAWNING"].includes(node.state)}
                isDone={node.state === "DONE"}
                isError={node.state === "ERROR"}
                isOpen={isOpen(node.node_id, node.state)}
                onToggle={() => handleToggleCard(node.node_id, node.state)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Welcome Screen ─────────────────────────────────────
function WelcomeScreen({ 
  onSend, 
  systemStatus 
}: { 
  onSend: (msg: string) => void;
  systemStatus: any;
}) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [greeting, setGreeting] = useState({ text: "Selamat Datang", sub: "Mulai hari dengan memantau kondisi lingkungan Bali.", icon: "🌿" });

  useEffect(() => {
    const calc = () => {
      const h = new Date().getHours();
      if (h >= 5 && h < 12) return { text: "Selamat Pagi", sub: "Mulai hari dengan memantau kondisi lingkungan Bali.", icon: "🌿" };
      if (h >= 12 && h < 15) return { text: "Selamat Siang", sub: "Pantau kondisi lingkungan Bali siang ini.", icon: "🌿" };
      if (h >= 15 && h < 19) return { text: "Selamat Sore", sub: "Perbarui data audit sore ini.", icon: "🌿" };
      return { text: "Selamat Malam", sub: "Pemantauan tetap berjalan malam ini.", icon: "🌿" };
    };
    setGreeting(calc());
    const t = setInterval(() => setGreeting(calc()), 60000);
    return () => clearInterval(t);
  }, []);

  const SUGGESTIONS = [
    { text: "Vegetasi Ubud", icon: <Leaf size={14} /> },
    { text: "Sungai Ayung", icon: <Waves size={14} /> },
    { text: "Polusi Udara Denpasar", icon: <Wind size={14} /> },
    { text: "Hotspot Kintamani", icon: <Flame size={14} /> },
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
      className="w-full max-w-2xl flex flex-col items-center gap-5 py-12"
    >
      <div className="text-center">
        <h1 className="text-4xl font-serif font-light mb-2.5 tracking-tight text-[var(--pemali-text-primary)]">
          {greeting.text}
        </h1>
        <p className="text-[var(--pemali-text-secondary)] text-sm">{greeting.sub}</p>
      </div>

      <div className="w-full flex flex-col items-center gap-5">
        {/* Grounded Chat Input Wrapper */}
        <div 
          className="w-full flex items-end gap-3 bg-[#e8e4dd] rounded-[9999px] px-5 py-[14px] shadow-[0_1px_4px_rgba(0,0,0,0.08)] focus-within:ring-1 focus-within:ring-[var(--pemali-accent)]/30 transition-all duration-300"
          title="Enter kirim · Shift+Enter baris baru"
        >

          
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
            }}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="Apa yang bisa saya bantu hari ini?"
            className="flex-1 bg-transparent text-[var(--pemali-text-primary)] placeholder-[var(--pemali-text-muted)] text-[14px] resize-none outline-none leading-relaxed max-h-[200px] overflow-y-auto pt-0.5"
            rows={1}
            style={{ minHeight: '24px' }}
          />

          <button
            onClick={handleSend}
            disabled={!value.trim()}
            className="w-7 h-7 mb-0.5 shrink-0 rounded-full bg-[var(--pemali-accent)] flex items-center justify-center disabled:opacity-30 hover:opacity-90 transition-opacity"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5"><path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"/></svg>
          </button>
        </div>

        {/* Suggestion Chips */}
        <div className="flex flex-wrap gap-2 justify-center">
          {SUGGESTIONS.map((s) => (
            <button
              key={s.text}
              onClick={() => onSend(s.text)}
              className="px-3.5 py-2 text-[11px] font-mono border border-[var(--pemali-border)] rounded-full text-[var(--pemali-text-secondary)] hover:text-[var(--pemali-text-primary)] hover:border-[var(--pemali-border-glow)] transition-all bg-[var(--pemali-surface)]/45 flex items-center gap-2 select-none"
            >
              <span>{s.icon}</span>
              <span>{s.text}</span>
            </button>
          ))}
        </div>


      </div>
    </motion.div>
  );
}

// ── Main Dashboard ─────────────────────────────────────
export default function PemaliDashboard() {
  const [historySearch, setHistorySearch] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const events = useTelemetryStore((s) => s.events);
  const isConnected = useTelemetryStore((s) => s.isConnected);
  const clearEvents = useTelemetryStore((s) => s.clearEvents);
  const setEvents = useTelemetryStore((s) => s.setEvents);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [finalReport, setFinalReport] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [auditMode, setAuditMode] = useState(false);
  const [observationView, setObservationView] = useState("process");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSearchExpanded, setIsSearchExpanded] = useState(false);
  const [mainView, setMainView] = useState<"chat" | "recents">("chat");
  const chatEndRef = useRef<HTMLDivElement>(null);

  const backendUrl = "";

  const [systemStatus, setSystemStatus] = useState<{
    fastapi_active: boolean;
    modules_loaded: number;
    concurrent_tasks_active: number;
    total_reports: number;
    total_sessions: number;
    recent_reports: any[];
  } | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/api/status`);
      if (res.ok) setSystemStatus(await res.json());
    } catch (err) { console.error("Status:", err); }
  }, [backendUrl]);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const currentModel = process.env.NEXT_PUBLIC_OPENROUTER_MODEL || "DEEPSEEK-R1";

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

  // Auto-refresh session list setiap 10 detik
  useEffect(() => {
    const interval = setInterval(loadSessions, 10000);
    return () => clearInterval(interval);
  }, [loadSessions]);

  // Fallback Polling — sinkronisasi riwayat jika SSE terputus/lambat
  useEffect(() => {
    if (!activeSessionId) return;

    let intervalId = setInterval(async () => {
      try {
        const res = await fetch(`${backendUrl}/api/history/${activeSessionId}`);
        if (res.ok) {
          const data = await res.json();
          const memories = data.agent_memories || [];
          const assistantMsgs = memories.filter((m: any) => m.role === "assistant");
          
          if (assistantMsgs.length > 0) {
            setMessages(prev => {
              const prevAssistantCount = prev.filter(m => m.role === "assistant").length;
              
              // Jika di database sudah ada respons asisten baru melebihi local state
              if (assistantMsgs.length > prevAssistantCount) {
                // Matikan indikator mengetik dan sinkronkan seluruh pesan
                setIsTyping(false);
                const mapped = memories.map((m: any) => ({
                  role: m.role,
                  content: m.content,
                  ts: m.timestamp ? new Date(m.timestamp).getTime() : Date.now()
                }));
                return mapped;
              }
              return prev;
            });
          }
        }
      } catch (err) {
        console.warn("[Polling Fallback] Error syncing history:", err);
      }
    }, 5000);

    return () => clearInterval(intervalId);
  }, [activeSessionId, backendUrl]);

  // Watch events from Zustand store (fed by NarrativeStream in root layout)
  useEffect(() => {
    if (events.length === 0) return;
    const event = events[events.length - 1];

    // Auto-switch to report on synthesis event
    if (event.node_id === "synthesis") {
      if (event.state === "DONE" && event.narrative) {
        setFinalReport(event.narrative);
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
        setTimeout(() => {
          setObservationView("report");
          setAuditMode(true);
        }, 1000);
      }
    }

    if (event.node_id === "manager" && (event.state === "DONE" || event.state === "ERROR")) {
      setIsTyping(false);
      if (event.narrative && event.metadata?.type !== "final_report") {
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && last.content === event.narrative) return prev;
          return [...prev, { role: "assistant", content: event.narrative, ts: Date.now() }];
        });
      }
    }

    const hasSubAgent = events.some(ev => 
      ev.node_type === "SubAgent" || 
      ev.node_type === "Manager" ||
      (ev as any).metadata?.plan
    );
    setAuditMode(hasSubAgent);
  }, [events]);

  const handleSelectSession = async (id: string) => {
    setActiveSessionId(id);
    setIsTyping(false);
    clearEvents();
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
          let node_id = m.name || "manager";
          
          if (!m.name) {
            const content = m.content.toLowerCase();
            if (content.includes("geo_agent") || content.includes("ndvi") || content.includes("satelit")) node_id = "geo_agent";
            else if (content.includes("water_agent") || content.includes("kualitas air") || content.includes("ph ") || content.includes("sungai") || content.includes("danau") || content.includes(" air ") || content.includes("hidrologi")) node_id = "water_agent";
            else if (content.includes("fire_agent") || content.includes("thermal") || content.includes("kebakaran") || content.includes("hotspot")) node_id = "fire_agent";
            else if (content.includes("osint_agent") || content.includes("berita") || content.includes("media") || content.includes("sentimen")) node_id = "osint_agent";
            else if (content.includes("scheduler_agent") || content.includes("jadwal") || content.includes("otomatis") || content.includes("rutin")) node_id = "scheduler_agent";
            else if (m.content.includes("# Laporan") || m.content.includes("# 🌿") || content.includes("audit selesai")) node_id = "synthesis";
          }

          return {
            node_id,
            state: "DONE",
            narrative: m.content, // Load full narrative content!
            type: "node_state",
            timestamp: new Date(m.created_at || Date.now()).getTime()
          };
        });
      setEvents(reconstructedEvents);

      // 2. Filter pesan untuk chat UI (Editorial Look)
      const chatHistory = (data.agent_memories || [])
        .filter((m: any) => {
          if (m.role === "user") return true;
          if (m.role === "assistant") {
            // Sembunyikan jika nama bukan "manager" (jika name diset)
            if (m.name) {
              if (m.name !== "manager") return false;
            } else {
              // Backward compatibility: sembunyikan laporan akhir dari chat bubble
              if (m.content.includes("# Laporan") || m.content.includes("# 🌿")) return false;
            }

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
    setMainView("chat");
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
      } else {
        setIsTyping(false);
        let errorMsg = "⚠️ Gagal memproses pesan.";
        try {
          const errData = await res.json();
          const detailStr = typeof errData.detail === "string" ? errData.detail.toLowerCase() : "";
          if (detailStr.includes("api key") || detailStr.includes("token") || detailStr.includes("openrouter")) {
            errorMsg = "🔑 **[API Key / Token Exhausted]**\n\nToken API OpenRouter tidak terkonfigurasi atau kuota limit Anda habis pada file `.env`.\n\nMohon periksa status `OPENROUTER_API_KEY` di server backend Anda.";
          } else {
            errorMsg = `❌ **[Internal Server Error ${res.status}]**\n\nTerjadi kegagalan pemrosesan pada backend:\n\`\`\`json\n${JSON.stringify(errData, null, 2)}\n\`\`\``;
          }
        } catch {
          errorMsg = `❌ **[Backend HTTP Error ${res.status}]**\n\nTerjadi kegagalan koneksi internal. Silakan periksa status log terminal uvicorn backend Anda.`;
        }
        setMessages(prev => [...prev, { role: "assistant", content: errorMsg, ts: Date.now() }]);
      }
    } catch (err) {
      setIsTyping(false);
      const networkErrorMsg = "🔌 **[Koneksi Backend Gagal]**\n\nBackend FastAPI PEMALI belum hidup atau tidak terhubung di `http://localhost:8080`.\n\nPastikan backend dijalankan terlebih dahulu dengan perintah `./run.sh` atau `uvicorn main:app --reload --port 8080` di terminal Anda.";
      setMessages(prev => [...prev, { role: "assistant", content: networkErrorMsg, ts: Date.now() }]);
    }
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
    <main className="h-screen w-full bg-[var(--pemali-bg)] flex flex-col overflow-hidden font-sans text-[var(--pemali-text-primary)]">
      {/* Main Layout Area */}
      <div className="flex-1 flex overflow-hidden w-full relative">
        
        {/* ── Left Sidebar (Claude.ai style) ── */}
        <div 
          className={`h-full shrink-0 flex flex-col bg-[var(--pemali-surface)] border-r border-stone-200 overflow-hidden transition-[width] duration-[250ms] ease-in-out z-20 ${
            isSidebarOpen ? "w-[260px]" : "w-[44px]"
          }`}
        >
          <div className="w-[260px] h-full flex flex-col">
            {/* Header inside sidebar */}
            <div className="px-3 pt-5 pb-3 flex items-center shrink-0">
              <button 
                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                className="w-5 h-5 flex items-center justify-center shrink-0 text-[var(--pemali-text-secondary)] hover:text-[var(--pemali-text-primary)] transition-colors"
                title="Toggle Sidebar"
              >
                <PanelLeft size={16} />
              </button>
              <div 
                className={`ml-3 font-serif text-2xl font-semibold tracking-tight text-[var(--pemali-text-primary)] leading-none select-none transition-opacity whitespace-nowrap ${
                  isSidebarOpen ? "opacity-100 duration-200 delay-100" : "opacity-0 duration-150 pointer-events-none"
                }`}
              >
                Pemali.
              </div>
            </div>

            <div className={`h-px bg-[var(--pemali-border)] mx-4 mb-2 shrink-0 transition-opacity ${
               isSidebarOpen ? "opacity-50 duration-200 delay-100" : "opacity-0 duration-150 pointer-events-none"
            }`} />

            {/* ── Nav Items ── */}
            <div className="px-1.5 py-2 flex flex-col gap-1 shrink-0">
              {/* New Audit */}
              <button onClick={handleNewAudit} className="flex items-center px-1.5 py-1 text-[var(--pemali-text-secondary)] hover:text-[var(--pemali-text-primary)] hover:bg-[var(--pemali-bg)] rounded-lg transition-colors w-full text-left" title="New Audit">
                <div className="w-5 flex items-center justify-center shrink-0"><Plus size={16} /></div>
                <span className={`ml-3 text-[13px] font-medium whitespace-nowrap transition-opacity ${isSidebarOpen ? "opacity-100 duration-200 delay-100" : "opacity-0 duration-150 pointer-events-none"}`}>New Audit</span>
              </button>
              {/* Search */}
              <button onClick={() => setIsSearchExpanded(true)} className="flex items-center px-1.5 py-1 text-[var(--pemali-text-secondary)] hover:text-[var(--pemali-text-primary)] hover:bg-[var(--pemali-bg)] rounded-lg transition-colors w-full text-left" title="Search">
                <div className="w-5 flex items-center justify-center shrink-0"><Search size={16} /></div>
                <span className={`ml-3 text-[13px] font-medium whitespace-nowrap transition-opacity ${isSidebarOpen ? "opacity-100 duration-200 delay-100" : "opacity-0 duration-150 pointer-events-none"}`}>Search</span>
              </button>
              {/* Chats */}
              <button onClick={() => setMainView("recents")} className={`flex items-center px-1.5 py-1 rounded-lg transition-colors w-full text-left ${mainView === "recents" && isSidebarOpen ? "bg-[var(--pemali-bg)] text-[var(--pemali-text-primary)]" : "text-[var(--pemali-text-secondary)] hover:text-[var(--pemali-text-primary)] hover:bg-[var(--pemali-bg)]"}`} title="Chats">
                <div className="w-5 flex items-center justify-center shrink-0"><MessageSquare size={16} /></div>
                <span className={`ml-3 text-[13px] font-medium whitespace-nowrap transition-opacity ${isSidebarOpen ? "opacity-100 duration-200 delay-100" : "opacity-0 duration-150 pointer-events-none"}`}>Chats</span>
              </button>
              {/* Platform */}
              <div className="flex items-center px-1.5 py-1">
                <Link href="/" className="flex items-center text-[var(--pemali-text-secondary)] hover:text-[var(--pemali-text-primary)] transition-colors w-full" title="Platform">
                  <div className="w-5 flex items-center justify-center shrink-0"><Home size={16} /></div>
                  <span className={`ml-3 text-[13px] font-medium whitespace-nowrap transition-opacity ${isSidebarOpen ? "opacity-100 duration-200 delay-100" : "opacity-0 duration-150 pointer-events-none"}`}>Platform</span>
                </Link>
              </div>
              {/* Status */}
              <div className="flex items-center px-1.5 py-1" title={isConnected ? "Sistem aktif" : "Sistem offline"}>
                <div className="w-5 flex items-center justify-center shrink-0">
                  <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-[var(--state-complete)]" : "bg-[var(--state-error)]"}`} />
                </div>
                <span className={`ml-3 text-[13px] font-medium text-[var(--pemali-text-muted)] whitespace-nowrap transition-opacity ${isSidebarOpen ? "opacity-100 duration-200 delay-100" : "opacity-0 duration-150 pointer-events-none"}`}>
                  {isConnected ? "Sistem aktif" : "Sistem offline"}
                </span>
              </div>
            </div>

            {/* ── Recents ── */}
            <div className={`flex flex-col flex-1 overflow-hidden transition-opacity ${isSidebarOpen ? "opacity-100 duration-200 delay-100" : "opacity-0 duration-150 pointer-events-none"}`}>
              <div className="px-4 py-1.5 mt-1 text-[10px] font-mono text-[var(--pemali-text-muted)] uppercase tracking-wider shrink-0">Recents</div>
              <div className="flex-1 overflow-y-auto px-3 scrollbar-none flex flex-col gap-1 pb-4">
              {(() => {
                const filtered = sessions.filter((s: any) => (s.title || "").toLowerCase().includes(historySearch.toLowerCase()));
                if (sessions.length === 0) return (
                  <div className="flex flex-col items-center justify-center h-full gap-2 opacity-50">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-[var(--pemali-text-muted)]"><path d="M12 8v4l3 3"/><circle cx="12" cy="12" r="9"/></svg>
                    <p className="text-[10px] text-[var(--pemali-text-muted)] font-mono">Belum ada sesi</p>
                  </div>
                );
                if (filtered.length === 0) return (
                  <div className="flex flex-col items-center justify-center mt-8 gap-2 opacity-50">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-[var(--pemali-text-muted)]"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
                    <p className="text-[10px] text-[var(--pemali-text-muted)] font-mono text-center">Tidak ada riwayat</p>
                  </div>
                );
                return filtered.map((s: any) => {
                  const isActive = activeSessionId === s.id;
                  const date = s.last_activity ? new Date(s.last_activity).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" }) : "";
                  return (
                    <button key={s.id} onClick={() => handleSelectSession(s.id)}
                      className={`w-full text-left px-3 py-2.5 rounded-xl transition-all group border ${isActive ? "bg-[var(--pemali-surface)] border-[var(--pemali-accent)]/20 shadow-sm" : "border-transparent hover:bg-[var(--pemali-surface)]/50 hover:border-[var(--pemali-border)]"}`}
                    >
                      <div className="flex items-start gap-2.5">
                        <div className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${isActive ? "bg-[var(--pemali-accent)]" : "bg-[var(--pemali-border)]"}`} />
                        <div className="flex-1 min-w-0">
                          <p className={`text-[12px] truncate leading-snug ${isActive ? "font-medium text-[var(--pemali-text-primary)]" : "text-[var(--pemali-text-secondary)] group-hover:text-[var(--pemali-text-primary)]"}`}>{s.title || "Sesi tanpa judul"}</p>
                          {date && <p className="text-[9px] font-mono text-[var(--pemali-text-muted)] mt-1 uppercase tracking-wide">{date}</p>}
                        </div>
                      </div>
                    </button>
                  );
                });
              })()}
              </div>
            </div>

          </div>
        </div>



        {/* ── Main Content Area ── */}
        <div className="flex-1 flex flex-col overflow-hidden relative bg-[var(--pemali-bg)]">
          

          
          {mainView === "recents" ? (
            <div className="flex-1 overflow-y-auto px-6 py-12 bg-[var(--pemali-bg)]">
              <div className="max-w-3xl mx-auto flex flex-col">
                <h1 className="text-xl font-serif text-[var(--pemali-text-primary)] mb-8">Chats</h1>
                
                <div className="relative mb-8">
                  <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--pemali-text-secondary)]" />
                  <input 
                    id="recents-search"
                    type="text" 
                    placeholder="Search chats..." 
                    value={historySearch}
                    onChange={(e) => setHistorySearch(e.target.value)}
                    className="w-full bg-[var(--pemali-surface)] border border-[var(--pemali-border)] rounded-xl pl-12 pr-4 py-3 text-[13px] text-[var(--pemali-text-primary)] placeholder-[var(--pemali-text-muted)] focus:outline-none focus:border-[var(--pemali-accent)]/50 transition-colors"
                  />
                </div>

                <div className="flex flex-col">
                  {sessions.filter((s: any) => (s.title || "").toLowerCase().includes(historySearch.toLowerCase())).length === 0 ? (
                    <div className="text-[13px] text-[var(--pemali-text-secondary)] text-center py-10">No chats found.</div>
                  ) : (
                    sessions.filter((s: any) => (s.title || "").toLowerCase().includes(historySearch.toLowerCase())).map((s: any) => {
                      const date = s.last_activity ? new Date(s.last_activity).toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" }) : "Recently";
                      return (
                        <div 
                          key={s.id} 
                          className="group border-b border-[var(--pemali-border)] hover:bg-[var(--pemali-surface)]/30 cursor-pointer transition-colors" 
                          onClick={() => { handleSelectSession(s.id); setMainView("chat"); }}
                        >
                          <div className="flex items-center justify-between px-2 py-4">
                            <span className="text-[13.5px] text-[var(--pemali-text-primary)] truncate max-w-[80%] group-hover:text-[var(--pemali-text-primary)] transition-colors">{s.title || "Sesi tanpa judul"}</span>
                            <span className="text-[11px] text-[var(--pemali-text-secondary)]">{date}</span>
                          </div>
                        </div>
                      )
                    })
                  )}
                </div>
              </div>
            </div>
          ) : (
            /* ── CHAT / AUDIT MODE ── */
            <div className="flex-1 flex overflow-hidden">
              {/* CENTER: DAG Visualizer — slides in when auditMode */}
              <div
                className={`h-full overflow-hidden transition-all duration-300 ${(auditMode && hasStarted) ? "shrink-0" : "shrink"}`}
                style={{
                  flex: (auditMode && hasStarted) ? "1 1 0" : "0 0 0",
                  opacity: (auditMode && hasStarted) ? 1 : 0,
                  width: (auditMode && hasStarted) ? "auto" : "0px",
                  minWidth: 0,
                  pointerEvents: (auditMode && hasStarted) ? "auto" : "none",
                }}
              >
                <DagVisualizer
                  events={events}
                  finalReport={finalReport}
                  messages={messages}
                  view={observationView}
                  onToggleView={() => setObservationView(
                    observationView === "report" ? "process" : "report"
                  )}
                />
              </div>

              {/* RIGHT: Chat Panel — fixed 380px when auditMode, centered 672px when simple chat or welcome */}
              <div
                className="h-full flex flex-col overflow-hidden shrink-0 transition-all duration-300 w-full"
                style={{
                  flex: (auditMode && hasStarted) ? "0 0 380px" : "1 1 0",
                  maxWidth: (auditMode && hasStarted) ? "380px" : "672px", // 672px matches max-w-2xl of the WelcomeScreen
                  margin: (auditMode && hasStarted) ? undefined : "0 auto",
                }}
              >
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

                    <div className="bg-[var(--pemali-bg)]/50 backdrop-blur-sm shrink-0">
                      <div className="px-4 pt-4 mb-[24px]">
                        <ChatInput onSend={handleSendMessage} disabled={isTyping} />
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex flex-col items-center pt-[28vh] px-6">
                    <WelcomeScreen onSend={handleSendMessage} systemStatus={systemStatus} />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>


      {/* ── Search Modal ── */}
      <AnimatePresence>
        {isSearchExpanded && (
          <motion.div 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 1 }} 
            exit={{ opacity: 0 }} 
            className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-black/60 backdrop-blur-[2px]"
            onClick={() => setIsSearchExpanded(false)}
          >
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: -10 }} 
              animate={{ opacity: 1, scale: 1, y: 0 }} 
              exit={{ opacity: 0, scale: 0.95, y: -10 }}
              transition={{ duration: 0.15 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-[600px] bg-[var(--pemali-surface)] border border-stone-200/20 rounded-xl shadow-2xl flex flex-col overflow-hidden"
            >
              <div className="flex items-center px-4 py-3 border-b border-stone-200/10">
                <Search size={16} className="text-[var(--pemali-text-secondary)] mr-3 shrink-0" />
                <input 
                  type="text" 
                  placeholder="Search chats and projects..." 
                  value={historySearch}
                  onChange={(e) => setHistorySearch(e.target.value)}
                  className="flex-1 bg-transparent border-none outline-none text-[14px] text-[var(--pemali-text-primary)] placeholder-[var(--pemali-text-muted)]" 
                  autoFocus 
                />
                <button 
                  onClick={() => setIsSearchExpanded(false)}
                  className="ml-2 text-[10px] font-mono text-[var(--pemali-text-secondary)] px-2 py-1 rounded bg-[var(--pemali-border)]/50 hover:text-[var(--pemali-text-primary)] transition-colors"
                >
                  ESC
                </button>
              </div>
              <div className="p-2 flex flex-col max-h-[400px] overflow-y-auto scrollbar-none">
                {sessions.filter((s: any) => (s.title || "").toLowerCase().includes(historySearch.toLowerCase())).length === 0 ? (
                  <div className="text-[13px] text-[var(--pemali-text-secondary)] text-center py-8">No results found.</div>
                ) : (
                  sessions.filter((s: any) => (s.title || "").toLowerCase().includes(historySearch.toLowerCase())).slice(0, 10).map((s: any) => {
                    const date = s.last_activity ? new Date(s.last_activity).toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" }) : "Recently";
                    return (
                      <button 
                        key={s.id}
                        onClick={() => { handleSelectSession(s.id); setMainView("chat"); setIsSearchExpanded(false); }}
                        className="flex items-center gap-3 w-full text-left px-3 py-2.5 rounded-lg hover:bg-[var(--pemali-bg)] transition-colors group"
                      >
                        <MessageSquare size={14} className="text-[var(--pemali-text-muted)] group-hover:text-[var(--pemali-text-primary)] transition-colors" />
                        <span className="flex-1 text-[13px] text-[var(--pemali-text-secondary)] group-hover:text-[var(--pemali-text-primary)] transition-colors truncate">
                          {s.title || "Sesi tanpa judul"}
                        </span>
                        <span className="text-[10px] font-mono text-[var(--pemali-text-muted)]">{date}</span>
                      </button>
                    )
                  })
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
