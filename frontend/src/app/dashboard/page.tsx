"use client";

import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
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
import { Cpu, Database, Activity, PanelLeft, Plus, Search, MessageSquare, Leaf, Waves, Wind, Flame, Home, Brain, Globe, Droplets, ChevronDown, ChevronUp, Check, AlertCircle, Calendar, FileText, Bot, Camera, CloudSun, Compass } from "lucide-react";

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

// ── Custom Flat SVGs for precise icon mappings ───────────
const InstagramIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    viewBox="0 0 24 24"
    width="20"
    height="20"
    stroke="currentColor"
    strokeWidth="2"
    fill="none"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
    <line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />
  </svg>
);

const EarthquakeIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    viewBox="0 0 24 24"
    width="20"
    height="20"
    stroke="currentColor"
    strokeWidth="2"
    fill="none"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    {/* Ground baseline */}
    <path d="M2 19h20" />
    
    {/* Ground cracks underneath */}
    <path d="M11 19l-1.5 2.5 3 2.5" />
    
    {/* Left tilted building */}
    <path d="M4 19l-1-8 4-1 1 9" />
    {/* Clean horizontal divider for left building */}
    <path d="M3.5 15l4-1" />
    
    {/* Middle straight but shaking building */}
    <path d="M9.5 19l1.5-12 4 0.5-1.5 11.5" />
    {/* Clean horizontal divider for middle building */}
    <path d="M10.2 13l4 0.5" />
    
    {/* Right tilted building */}
    <path d="M16 19l1.5-7 4 1-1.5 6" />
    {/* Clean horizontal divider for right building */}
    <path d="M16.7 15.5l4 1" />
    
    {/* Shaking vibration waves on the left */}
    <path d="M1.5 8.5l1.5 1.5-1.5 1.5" />
    {/* Shaking vibration waves on the right */}
    <path d="M22.5 8.5l-1.5 1.5 1.5 1.5" />
  </svg>
);

// ── Agent Metadata & Icons mapping (no emoji) ───────────
const AGENT_META: Record<string, { name: string; subtitle: string; icon: React.ComponentType<any> }> = {
  manager: {
    name: "Manager Agent",
    subtitle: "STRATEGIC PLANNING",
    icon: Cpu,
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
  system_scheduler: {
    name: "System Scheduler Agent",
    subtitle: "COGNITIVE SUB-AGENT",
    icon: Calendar,
  },
  synthesis: {
    name: "Synthesis Agent",
    subtitle: "FINAL RECOMMENDATIONS",
    icon: FileText,
  },
  air_quality_index: {
    name: "Air Quality Index Agent",
    subtitle: "COGNITIVE SUB-AGENT",
    icon: Wind,
  },
  weather_hazard_monitor: {
    name: "Weather Hazard Monitor Agent",
    subtitle: "COGNITIVE SUB-AGENT",
    icon: CloudSun,
  },
  fire_hotspot_detector: {
    name: "Fire Hotspot Detector Agent",
    subtitle: "COGNITIVE SUB-AGENT",
    icon: Flame,
  },
  osint_web_search: {
    name: "Osint Web Search Agent",
    subtitle: "COGNITIVE SUB-AGENT",
    icon: Search,
  },
  osint_trend_scanner: {
    name: "Osint Trend Scanner Agent",
    subtitle: "COGNITIVE SUB-AGENT",
    icon: Search,
  },
  osint_instagram_monitor: {
    name: "Osint Instagram Monitor Agent",
    subtitle: "COGNITIVE SUB-AGENT",
    icon: InstagramIcon,
  },
  sea_level_tide_monitor: {
    name: "Sea Level & Tide Agent",
    subtitle: "COGNITIVE SUB-AGENT",
    icon: Waves,
  },
  earthquake_risk_monitor: {
    name: "Earthquake Risk Agent",
    subtitle: "COGNITIVE SUB-AGENT",
    icon: EarthquakeIcon,
  },
};

const getAgentMeta = (nodeId: string) => {
  return AGENT_META[nodeId] || {
    name: nodeId.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()) + " Agent",
    subtitle: "COGNITIVE SUB-AGENT",
    icon: Bot,
  };
};

interface NodeData {
  node_id: string;
  state: string;
  narrative: string;
  node_type: string;
  tool_name?: string;
}

// ── Agent Metadata & Skills Mapping ──────────────────────
const AGENT_SKILLS: Record<string, string[]> = {
  manager: ["Strategizing & DAG Task Planning", "Multi-Agent Coordination", "ChromaDB Context Retrieval"],
  geo_agent: ["Sentinel-2 NDVI Vegetation Audit", "Spatial Imagery Mapping", "Forest Canopy Analysis"],
  water_agent: ["Water pH/Oxygen IoT Analysis", "Ayung River Sensor Audit", "Tri Hita Karana Hydro Balance"],
  fire_agent: ["MODIS Hotspot Thermal Detection", "Fire Hazard Intensity Mapping", "Risk Mitigation Alerting"],
  osint_agent: ["Local News Scraping & Extraction", "Web Search API Audit", "Social Public Sentiment"],
  scheduler_agent: ["Tick Daemon Loop Integration", "State Machine Chron Audit"],
  synthesis: ["Parahyangan-Pawongan-Palemahan Matrix Synthesis", "Grounded Narrative Audit Report Generator"]
};

const getAgentSkills = (nodeId: string) => {
  return AGENT_SKILLS[nodeId] || ["Cognitive Agent Domain Inference", "UTI Module Protocol Execution"];
};

// ── TypewriterText (untuk efek mengetik narasi subagent dengan lancar saat streaming) ───
function TypewriterText({ text, active }: { text: string; active: boolean }) {
  const [displayed, setDisplayed] = useState("");
  const currentTextRef = useRef("");
  
  useEffect(() => {
    if (!text) {
      setDisplayed("");
      currentTextRef.current = "";
      return;
    }
    
    // Jika teks bertambah (SSE incremental update), ketikkan sisa tambahannya
    if (text.startsWith(currentTextRef.current)) {
      const newPart = text.slice(currentTextRef.current.length);
      if (!newPart) return;
      
      let index = 0;
      const step = newPart.length > 50 ? 4 : 1;
      const interval = newPart.length > 50 ? 5 : 15;
      
      const timer = setInterval(() => {
        index += step;
        if (index >= newPart.length) {
          setDisplayed(text);
          currentTextRef.current = text;
          clearInterval(timer);
        } else {
          setDisplayed(currentTextRef.current + newPart.substring(0, index));
        }
      }, interval);
      
      return () => clearInterval(timer);
    } else {
      // Jika teks berubah total (session baru / reset), jalankan pengetikan penuh
      let index = 0;
      const step = text.length > 500 ? 5 : text.length > 200 ? 3 : 1;
      const interval = text.length > 500 ? 5 : 12;
      
      const timer = setInterval(() => {
        index += step;
        if (index >= text.length) {
          setDisplayed(text);
          currentTextRef.current = text;
          clearInterval(timer);
        } else {
          setDisplayed(text.substring(0, index));
        }
      }, interval);
      
      return () => clearInterval(timer);
    }
  }, [text]);

  return <span>{displayed}</span>;
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
  const skills = getAgentSkills(node.node_id);

  const [typedText, setTypedText] = useState("");
  const cardEndRef = useRef<HTMLDivElement>(null);
  const liveThinkingText = useTelemetryStore((s) => s.thinkingStates[node.node_id]?.text || "");
  
  useEffect(() => {
    if (isActive) {
      setTypedText(liveThinkingText);
    } else {
      setTypedText(node.narrative || "");
    }
  }, [liveThinkingText, node.narrative, isActive]);

  const isTyping = isActive && liveThinkingText.length > 0;

  useEffect(() => {
    if (isTyping) {
      cardEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [typedText, isTyping]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.25, 0.1, 0.25, 1] }}
      className={`w-full bg-[#faf9f6] rounded-xl border overflow-hidden transition-all duration-500 ${
        isActive ? "active-agent-card border-[var(--pemali-accent)]/30 ring-1 ring-[var(--pemali-accent)]/5" : ""
      }`}
      style={{
        borderColor: isDone ? "#10B981" : isError ? "#EF4444" : isActive ? "rgba(139,92,246,0.3)" : "#e5e2dc",
        boxShadow: isActive ? "0 4px 12px rgba(139,92,246,0.03)" : "0 1px 3px rgba(0,0,0,0.01)",
      }}
    >
      {/* Header Row */}
      <div 
        onClick={onToggle}
        className="px-5 py-4.5 flex items-start justify-between cursor-pointer select-none hover:bg-black/[0.01] transition-colors"
      >
        <div className="flex items-start gap-4">
          <div 
            className="w-10 h-10 rounded-xl flex items-center justify-center border shrink-0 mt-0.5"
            style={{
              borderColor: isDone ? "#d1fae5" : isError ? "#fee2e2" : isActive ? "rgba(139,92,246,0.2)" : "#e5e2dc",
              backgroundColor: isDone ? "#f0fdf4" : isError ? "#fef2f2" : isActive ? "rgba(139,92,246,0.05)" : "#ffffff",
              color: isDone ? "#059669" : isError ? "#dc2626" : isActive ? "var(--pemali-accent)" : "#7a7670",
              transition: "all 500ms ease",
            }}
          >
            {Icon && <Icon size={20} />}
          </div>
          <div>
            <h4 className="text-[14px] font-bold text-[#1A1916] leading-none mb-1.5 flex items-center flex-wrap gap-2">
              <span>{meta.name}</span>
              {node.tool_name && (
                <span className="text-[9px] font-mono tracking-wider lowercase bg-[#f2efe9] px-1.5 py-0.5 rounded text-[#7a7670] border border-[#e5e2dc]">
                  modul: {node.tool_name}
                </span>
              )}
            </h4>
            <p className="text-[9px] font-mono tracking-widest text-[#999] uppercase leading-none mb-2.5">
              {meta.subtitle}
            </p>
            {/* Display Skills badges */}
            <div className="flex flex-wrap gap-1">
              {skills.map((s, idx) => (
                <span key={idx} className="text-[9px] font-mono text-[#7A7670] bg-[#f2efe9]/60 px-1.5 py-0.5 rounded border border-[#e5e2dc]/40">
                  {s}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
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
        {isOpen && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="border-t border-[#e5e2dc] bg-black/[0.005]"
          >
            <div className="px-5 py-4 font-mono text-[11px] text-[#7A7670] leading-relaxed whitespace-pre-wrap relative">
              <div className="text-[12px] text-[#555] font-sans italic opacity-60 mb-2 font-light">
                {isTyping ? "✦ AI sedang menalar..." : "✦ Hasil penalaran:"}
              </div>
              <span className="font-mono text-[#52525B] tracking-tight">
                {typedText ? (
                  <TypewriterText text={typedText} active={isActive} />
                ) : isTyping ? (
                  <span className="inline-flex items-center gap-2 text-[#7A7670] italic animate-pulse">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--pemali-accent)] animate-ping shrink-0" />
                    Menginisialisasi modul kognitif...
                  </span>
                ) : (
                  "Proses berjalan tanpa catatan log."
                )}
              </span>
              {isTyping && typedText.length > 0 && (
                <span className="inline-block animate-pulse font-sans font-bold text-[var(--pemali-accent)] ml-0.5">█</span>
              )}
              <div ref={cardEndRef} />
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
  onCloseSplitView,
}: {
  events: TelemetryEvent[];
  finalReport: string | null;
  messages: Message[];
  view: string;
  onToggleView: () => void;
  onCloseSplitView?: () => void;
}) {
  // Filter out IDLE nodes and synthesis node so they are progressively revealed one-by-one
  const allNodes = useMemo(() => {
    const nodeMap = new Map<string, NodeData>();
    for (const ev of events) {
      if (!ev.node_id || ev.node_id === "system") continue;
      // Exclude report text from agent reasoning narrative area, but preserve existing narrative if already parsed
      const isReportText = ev.narrative && (ev.narrative.startsWith("#") || ev.metadata?.type === "final_report" || ev.metadata?.type === "synthesis");
      const prev = nodeMap.get(ev.node_id);
      nodeMap.set(ev.node_id, {
        node_id: ev.node_id,
        state: ev.state,
        narrative: isReportText ? (prev?.narrative || "") : (ev.narrative || prev?.narrative || ""),
        node_type: (ev as any).node_type || prev?.node_type || "",
        tool_name: (ev as any).metadata?.tool_name || prev?.tool_name,
      });
    }
    return [...nodeMap.values()].filter(n => n.state !== "IDLE" && n.node_id !== "synthesis");
  }, [events]);

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
  const bodyContainerRef = useRef<HTMLDivElement>(null);
  const [prevNodesCount, setPrevNodesCount] = useState(0);

  // Determine if a card should be open
  const isOpen = (nodeId: string, state: string) => {
    if (manualExpanded.has(nodeId)) {
      return manualExpanded.get(nodeId)!;
    }
    // Default: open all active and completed nodes to let user review full thinking process
    return state !== "IDLE";
  };

  const handleToggleCard = (nodeId: string, currentState: string) => {
    setManualExpanded(prev => {
      const copy = new Map(prev);
      const currentOpen = isOpen(nodeId, currentState);
      copy.set(nodeId, !currentOpen);
      return copy;
    });
  };

  // Scroll active card into view secara otomatis HANYA ketika agent baru pertama kali ditemukan
  useEffect(() => {
    if (allNodes.length > prevNodesCount) {
      setPrevNodesCount(allNodes.length);
      setTimeout(() => {
        if (bodyContainerRef.current) {
          const activeCard = bodyContainerRef.current.querySelector(".active-agent-card");
          if (activeCard) {
            activeCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
          }
        }
      }, 300);
    }
  }, [allNodes.length, prevNodesCount]);

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
        <div className="flex items-center gap-4">
          {view === "report" && (
            <button
              onClick={onToggleView}
              className="text-[10px] font-mono text-[#7A7670] hover:text-[#1A1916] transition-colors"
            >
              ← Lihat Alur Kerja
            </button>
          )}
          {onCloseSplitView && (
            <button
              onClick={onCloseSplitView}
              className="text-[10px] font-mono text-[var(--pemali-accent)] hover:text-[#7C3AED] hover:underline transition-all flex items-center gap-1 font-semibold"
              title="Kembali ke chat normal"
            >
              Tutup Alur Kerja ✕
            </button>
          )}
        </div>
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
      <div 
        ref={bodyContainerRef}
        className="flex-1 overflow-y-auto px-6 pb-6 scrollbar-none"
      >
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
          <div className="flex flex-col my-4 ml-6">
            {allNodes.map((node, index) => {
              const active = ["EXECUTING", "THINKING", "SPAWNING"].includes(node.state);
              const done = node.state === "DONE";
              const error = node.state === "ERROR";
              const isLast = index === allNodes.length - 1;
              const lineColor = done ? "#10B981" : active ? "var(--pemali-accent)" : "#e5e2dc";

              return (
                <div key={node.node_id} className="flex items-stretch" style={{ gap: 16, marginBottom: isLast ? 0 : 12 }}>
                  {/* Kolom kiri: bullet (top-aligned) + line segment ke bawah */}
                  <div className="flex flex-col items-center flex-shrink-0" style={{ width: 8 }}>
                    {/* Spacer atas: dorong bullet sejajar header card (~25px) */}
                    <div style={{ height: 25, flexShrink: 0 }} />
                    {/* Bullet */}
                    <div
                      className="flex-shrink-0 transition-all duration-500 relative"
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        border: `1.5px solid ${done ? "#10B981" : error ? "#EF4444" : active ? "var(--pemali-accent)" : "#d4d0c9"}`,
                        background: done ? "#f0fdf4" : active ? "rgba(139,92,246,0.08)" : "#ffffff",
                        boxShadow: active
                          ? "0 0 8px rgba(139,92,246,0.4)"
                          : done
                            ? "0 0 6px rgba(16,185,129,0.35)"
                            : "none",
                      }}
                    >
                      {active && (
                        <span
                          className="absolute rounded-full animate-ping opacity-40"
                          style={{ inset: -3, background: "var(--pemali-accent)" }}
                        />
                      )}
                    </div>
                    {/* Line segment + arrowhead ke node berikutnya */}
                    {!isLast && (
                      <div className="flex-1 relative flex justify-center" style={{ minHeight: 12, marginBottom: -12 }}>
                        {/* Garis vertikal */}
                        <div
                          className="transition-colors duration-500"
                          style={{
                            width: 1.5,
                            height: "calc(100% - 5px)", // sisakan ruang untuk arrow
                            background: lineColor,
                          }}
                        />
                        {/* Arrowhead SVG di ujung bawah */}
                        <svg
                          width="10"
                          height="8"
                          viewBox="0 0 10 8"
                          fill="none"
                          className="absolute bottom-0 transition-all duration-500"
                          style={{ left: "50%", transform: "translateX(-50%)" }}
                        >
                          <path d="M5 8L0 0h10L5 8z" fill={lineColor} />
                        </svg>
                      </div>
                    )}

                  </div>

                  {/* Kolom kanan: card */}
                  <div className="flex-1 min-w-0">
                    <AgentThinkingCard
                      node={node}
                      isActive={active}
                      isDone={done}
                      isError={error}
                      isOpen={isOpen(node.node_id, node.state)}
                      onToggle={() => handleToggleCard(node.node_id, node.state)}
                    />
                  </div>
                </div>
              );
            })}
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
    { 
      label: "Audit vegetasi & deforestasi di Ubud", 
      prompt: "Audit vegetasi dan deforestasi di daerah Ubud menggunakan sensor MODIS/NDVI", 
      icon: <Leaf size={13} className="text-[#7a7670]" /> 
    },
    { 
      label: "Analisis kualitas air Sungai Ayung", 
      prompt: "Analisis kualitas air Sungai Ayung dan hidrologi sekitarnya", 
      icon: <Waves size={13} className="text-[#7a7670]" /> 
    },
    { 
      label: "Pantau polusi udara kota Denpasar", 
      prompt: "Pantau polusi udara dan kualitas partikulat PM2.5 di kota Denpasar", 
      icon: <Wind size={13} className="text-[#7a7670]" /> 
    },
    { 
      label: "Deteksi potensi kebakaran di daerah Kintamani", 
      prompt: "Deteksi titik panas kebakaran hutan (hotspot) di wilayah Kintamani", 
      icon: <Flame size={13} className="text-[#7a7670]" /> 
    },
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
        <div className="flex flex-wrap gap-2.5 justify-center mt-1">
          {SUGGESTIONS.map((s) => (
            <button
              key={s.label}
              onClick={() => onSend(s.prompt)}
              className="px-4 py-2.5 text-[12px] font-sans border border-[#d0ccc0] rounded-full text-[#1A1916] hover:text-[#1A1916] hover:border-[#c8a882] hover:bg-[#e8e4dd] transition-all bg-[#f0ede6] shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex items-center gap-2 select-none active:scale-[0.97]"
            >
              <span>{s.icon}</span>
              <span>{s.label}</span>
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
  const clearThinkingStates = useTelemetryStore((s) => s.clearThinkingStates);
  const setEvents = useTelemetryStore((s) => s.setEvents);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [finalReport, setFinalReport] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [auditMode, setAuditMode] = useState(false);
  const [observationView, setObservationView] = useState("process");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isSearchExpanded, setIsSearchExpanded] = useState(false);
  const [mainView, setMainView] = useState<"chat" | "recents">("chat");
  const chatEndRef = useRef<HTMLDivElement>(null);

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";

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

    // Handle synthesis event - display report in chat, keep center as process
    if (event.node_id === "synthesis") {
      if (event.state === "DONE" && event.narrative) {
        setFinalReport(event.narrative);
        setIsTyping(false);
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last?.content.includes("# Laporan") || last?.content.includes("# 🌿")) return prev;
          return [...prev, { 
            role: "assistant", 
            content: event.narrative, 
            ts: Date.now() 
          }];
        });
        setTimeout(() => {
          setObservationView("process");
          setAuditMode(false);
        }, 500);
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

    if (event.state === "ERROR") {
      setIsTyping(false);
    }

    const hasSynthesisDone = events.some(ev => ev.node_id === "synthesis" && ev.state === "DONE");
    if (!finalReport && !hasSynthesisDone) {
      const hasSubAgent = events.some(ev => 
        ev.node_type === "SubAgent" || 
        (ev.node_type === "Manager" && ev.metadata?.type !== "chat_response") ||
        (ev as any).metadata?.plan
      );
      setAuditMode(hasSubAgent);
    }
  }, [events]);

  const handleSelectSession = async (id: string) => {
    setActiveSessionId(id);
    setIsTyping(false);
    clearEvents();
    clearThinkingStates();
    setFinalReport(null);
      setAuditMode(false);
      setObservationView("process");

      try {
        const res = await fetch(`${backendUrl}/api/history/${id}`);
        if (!res.ok) throw new Error("Gagal mengambil histori");
        const data = await res.json();
        
        setActiveSessionId(id);
        setHasStarted(true);
        
        // 1. Load telemetry events dari DB (real events, bukan reconstruction)
        const telemetryEvents: any[] = (data.agent_memories || [])
        .filter((m: any) => m.role === "telemetry")
        .map((m: any) => {
          try {
            const ev = JSON.parse(m.content);
            return { ...ev, timestamp: ev.timestamp || new Date(m.created_at || Date.now()).getTime() };
          } catch { return null; }
        })
        .filter(Boolean);

        // 1b. Fallback: Rekonstruksi Telemetry dari memory untuk DAG
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
        // Gunakan telemetry events dari DB kalau ada, fallback ke reconstruction
        setEvents(telemetryEvents.length > 0 ? telemetryEvents : reconstructedEvents);

      // 2. Filter pesan untuk chat UI (Editorial Look)
      const chatHistory = (data.agent_memories || [])
        .filter((m: any) => {
          if (m.role === "user") return true;
          if (m.role === "assistant") {
            // Sembunyikan jika nama bukan "manager" (jika name diset)
            if (m.name) {
              if (m.name !== "manager") return false;
            } else {
              // Backward compatibility: sembunyikan laporan akhir dari chat bubble biasa (kita gabungkan di akhir)
              if (m.content.includes("# Laporan") || m.content.includes("# 🌿")) return false;
            }

            const trimmed = m.content.trim();
            const isJson = trimmed.startsWith("{") && trimmed.endsWith("}");
            if (isJson) {
              try {
                const parsed = JSON.parse(trimmed);
                // Sembunyikan jika ini telemetry event
                if (parsed.trace_id || parsed.node_id || parsed.node_type || parsed.state || parsed.event) return false;
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

      // 3. Cari laporan di audit_logs atau fallback ke memories untuk instant load
      const report = (data.audit_logs || []).find(
        (l: any) => l.narrative_report && (l.narrative_report.includes("#") || l.narrative_report.includes("🌿"))
      );
      
      let finalReportText: string | null = null;
      if (report) {
        finalReportText = report.narrative_report;
      } else {
        const reportInMemory = (data.agent_memories || [])
          .reverse()
          .find((m: any) => m.role === "assistant" && (m.content.includes("# Laporan") || m.content.includes("# 🌿")));
        if (reportInMemory) {
          finalReportText = reportInMemory.content;
        }
      }

      if (finalReportText) {
        setFinalReport(finalReportText);
        setAuditMode(false);
        setObservationView("report");

        // Gabungkan langsung ke chatHistory untuk Instant-Load bebas delay!
        chatHistory.push({
          role: "assistant",
          content: finalReportText,
          ts: Date.now()
        });
      } else {
        setFinalReport(null);
        setAuditMode(false);
        setObservationView("process");
      }

      setMessages(chatHistory);
    } catch (err) {
      console.error("Error loading history:", err);
    }
  };

  const handleNewAudit = () => {
    setActiveSessionId(null);
    setMessages([]);
    clearEvents();
    clearThinkingStates();
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
    clearEvents();
    clearThinkingStates();

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
              {/* Agentic */}
              <div className="flex items-center px-1.5 py-1">
                <Link href="/agentic" className="flex items-center text-[var(--pemali-text-secondary)] hover:text-[var(--pemali-text-primary)] transition-colors w-full" title="Agentic">
                  <div className="w-5 flex items-center justify-center shrink-0"><Bot size={16} /></div>
                  <span className={`ml-3 text-[13px] font-medium whitespace-nowrap transition-opacity ${isSidebarOpen ? "opacity-100 duration-200 delay-100" : "opacity-0 duration-150 pointer-events-none"}`}>Agentic</span>
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
                  onCloseSplitView={() => setAuditMode(false)}
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
                            setObservationView("process");
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
