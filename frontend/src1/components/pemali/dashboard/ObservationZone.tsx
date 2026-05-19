"use client";

import React, { useMemo, useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Brain,
  Satellite,
  Droplets,
  Flame,
  Globe,
  Calendar,
  FileText,
  Clock,
  Zap,
} from "lucide-react";
import { extractDagFromPlan, type TelemetryEvent } from "@/lib/dashboard";

// ── Icons ──
const Icons = {
  Brain: ({ className }: { className?: string }) => (
    <img src="/logo.png" alt="PEMALI Logo" className={className || "w-full h-full object-contain"} />
  ),
  Satellite: () => <Satellite size={20} />,
  Drop: () => <Droplets size={20} />,
  Flame: () => <Flame size={20} />,
  Globe: () => <Globe size={20} />,
  Calendar: () => <Calendar size={20} />,
  FileText: () => <FileText size={20} />,
  Clock: () => <Clock size={12} />,
  Zap: () => <Zap size={14} />,
};

// ── Observation Welcome Screen ──
function ObservationWelcome() {
  const container = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } },
  };
  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
  };

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="flex-1 flex flex-col items-center justify-center p-12 text-center"
    >
      <motion.div variants={item} className="w-16 h-16 rounded-full bg-[var(--pemali-accent)]/10 flex items-center justify-center text-[var(--pemali-accent)] mb-8">
        <Icons.Brain />
      </motion.div>
      <motion.h2 variants={item} className="text-3xl font-semibold mb-3 tracking-tight" style={{ fontFamily: "'Lora', serif" }}>
        Cognitive Observation Zone
      </motion.h2>
      <motion.p variants={item} className="text-[15px] text-[var(--pemali-text-secondary)] max-w-md leading-relaxed mb-12">
        Alur kerja agentik akan divisualisasikan di sini secara real-time saat audit dimulai.
      </motion.p>

      <motion.div variants={item} className="grid grid-cols-2 gap-4 w-full max-w-xl">
        {[
          { label: "Perencanaan Otonom", desc: "Manager menyusun strategi audit berdasarkan input" },
          { label: "Eksekusi Paralel", desc: "Sub-agent bekerja secara bersamaan sesuai kebutuhan" },
          { label: "Sintesis Data", desc: "Penggabungan temuan dari berbagai sumber" },
          { label: "Penyelarasan THK", desc: "Validasi laporan dengan kearifan lokal Bali" },
        ].map(f => (
          <div key={f.label} className="p-4 rounded-xl border border-[var(--pemali-border)] bg-[var(--pemali-surface)] text-left">
            <div className="text-[13px] font-semibold text-[var(--pemali-text-primary)] mb-1">{f.label}</div>
            <div className="text-[11px] text-[var(--pemali-text-muted)]">{f.desc}</div>
          </div>
        ))}
      </motion.div>
    </motion.div>
  );
}

// ── Typewriter Hook ──
function useTypewriter(text: string, speed: number = 30) {
  const [displayed, setDisplayed] = useState("");
  const [isComplete, setIsComplete] = useState(true);
  const posRef = useRef(0);
  const prevTextRef = useRef("");
  const textRef = useRef(text);
  textRef.current = text;

  // Reset hanya ketika teks diganti total (agent baru)
  useEffect(() => {
    const isNewSource = text === ""
      || (prevTextRef.current !== ""
        && !text.startsWith(prevTextRef.current)
        && text !== prevTextRef.current);
    if (isNewSource) {
      posRef.current = 0;
      setDisplayed("");
      setIsComplete(false);
    }
    prevTextRef.current = text;
  }, [text]);

  // Ngetik terus — pake textRef biar selalu baca teks terbaru (gak stale closure)
  useEffect(() => {
    if (!textRef.current) { setIsComplete(true); return; }
    if (posRef.current >= textRef.current.length) { setIsComplete(true); return; }

    setIsComplete(false);
    const interval = setInterval(() => {
      posRef.current++;
      setDisplayed(textRef.current.slice(0, posRef.current));
      if (posRef.current >= textRef.current.length) {
        setIsComplete(true);
        clearInterval(interval);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed]);

  return { displayed, isComplete };
}

// ── Agent Status Bar (collapsed) ──
function AgentStatusBar({ icon, title, subtitle, snippet }: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  snippet?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-4 w-full p-4 rounded-xl bg-[var(--pemali-surface)]/50 border border-[var(--pemali-border)] opacity-80 hover:opacity-100 transition-opacity"
    >
      <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <div className="text-[13px] font-semibold text-[var(--pemali-text-primary)]">{title}</div>
          <div className="text-[9px] px-2 py-0.5 rounded-full border border-emerald-500/30 text-emerald-400 bg-emerald-500/5 font-mono uppercase tracking-tighter shrink-0 ml-2">
            Selesai
          </div>
        </div>
        <div className="text-[10px] text-[var(--pemali-text-muted)] font-mono uppercase tracking-wider">{subtitle}</div>
        {snippet && (
          <div className="mt-2 text-[11px] text-[var(--pemali-text-secondary)] leading-relaxed line-clamp-2 border-t border-[var(--pemali-border)]/30 pt-2">
            {snippet}
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ── Connector Line (antar card) ──
function ConnectorLine() {
  return (
    <div className="flex flex-col items-center -my-3 relative z-10">
      <div className="w-[2px] h-7 bg-gradient-to-b from-[var(--pemali-accent)]/40 to-[var(--pemali-accent)]/10 rounded-full" />
      <div className="w-1.5 h-1.5 rounded-full bg-[var(--pemali-accent)]/30 mt-0.5" />
    </div>
  );
}

// ── Phase Progress ──
const PHASE_LABEL: Record<string, string> = {
  planning: "Planning",
  execute: "Execute",
  validate: "Validate",
  synthesis: "Synthesis",
  done: "Done",
};

function PhaseDots({ currentPhase }: { currentPhase: string }) {
  const order = ["planning", "execute", "synthesis", "done"];
  const nowIdx = order.indexOf(currentPhase);

  return (
    <div className="flex items-center gap-3 w-full px-2 py-4">
      {order.map((phase, idx) => {
        const isActive = idx <= nowIdx;
        const isNow = idx === nowIdx;
        return (
          <React.Fragment key={phase}>
            <div className="flex items-center gap-2">
              <div className={`relative w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold transition-all duration-700 ${
                isNow
                  ? "bg-[var(--pemali-accent)] text-white shadow-lg shadow-[var(--pemali-accent)]/30 scale-110"
                  : isActive
                  ? "bg-[var(--pemali-accent)]/20 text-[var(--pemali-accent)]"
                  : "bg-zinc-800/40 text-zinc-600"
              }`}>
                {idx + 1}
                {isNow && <div className="absolute inset-0 rounded-full animate-ping bg-[var(--pemali-accent)]/20" />}
              </div>
              <span className={`text-[10px] font-semibold uppercase tracking-wider hidden sm:inline transition-colors duration-700 ${
                isActive ? "text-[var(--pemali-text-primary)]" : "text-zinc-600"
              }`}>
                {PHASE_LABEL[phase] || phase}
              </span>
            </div>
            {idx < order.length - 1 && (
              <div className={`flex-1 h-[2px] rounded-full transition-all duration-700 ${
                idx < nowIdx
                  ? "bg-gradient-to-r from-[var(--pemali-accent)] to-[var(--pemali-accent)]/30"
                  : "bg-zinc-800/40"
              }`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ── Agent Area ──
const agentDisplay: Record<string, { title: string; subtitle: string; icon: React.ReactNode }> = {
  geo_agent: { title: "Satellite Imagery", subtitle: "geo_agent (NDVI)", icon: <Icons.Satellite /> },
  water_agent: { title: "Water Audit", subtitle: "water_agent (Sensors)", icon: <Icons.Drop /> },
  fire_agent: { title: "Fire Monitor", subtitle: "fire_agent (Thermal)", icon: <Icons.Flame /> },
  osint_agent: { title: "OSINT", subtitle: "osint_agent", icon: <Icons.Globe /> },
  scheduler_agent: { title: "System Scheduler", subtitle: "Autonomous Loop", icon: <Icons.Calendar /> },
};

export function AgentArea({ events }: { events: TelemetryEvent[] }) {
  const dagPlan = useMemo(() => extractDagFromPlan(events), [events]);
  const agentOrder = dagPlan.agents;

  const doneSet = useMemo(() => {
    const set = new Set<string>();
    events.forEach(e => {
      if ((e.state === "DONE" || e.state === "ERROR") && e.node_id) set.add(e.node_id);
    });
    return set;
  }, [events]);

  const hasAgentActivity = useMemo(() => {
    return events.some(e =>
      e.node_id !== "manager" && e.node_id !== "synthesis" && e.node_id !== "system" &&
      (e.state === "THINKING" || e.state === "EXECUTING" || e.state === "DONE")
    );
  }, [events]);

  const [currentIdx, setCurrentIdx] = useState(0);
  const isSynthesisDone = events.some(e => e.node_id === "synthesis" && e.state === "DONE");
  const showSynthesis = currentIdx >= agentOrder.length && agentOrder.length > 0;

  // Speed through remaining agents after synthesis done
  const fastMode = isSynthesisDone;

  // Phase selaras dengan visual flow
  const visualPhase = useMemo(() => {
    if (isSynthesisDone) return "done";
    if (showSynthesis) return "synthesis";
    if (hasAgentActivity) return "execute";
    return "planning";
  }, [isSynthesisDone, showSynthesis, hasAgentActivity]);

  // Narrative untuk current agent (declared first, used by typewriter + advance logic)
  const activeAgent = currentIdx < agentOrder.length ? agentOrder[currentIdx] : null;
  const agentNarrative = useMemo(() => {
    if (!activeAgent) return "";
    return events
      .filter(e => e.node_id === activeAgent && e.narrative)
      .map(e => e.narrative)
      .join("\n\n");
  }, [events, activeAgent]);

  const { displayed: typedText, isComplete: typingDone } = useTypewriter(agentNarrative, 30);

  // Advance currentIdx when agent is done AND typewriter complete
  useEffect(() => {
    if (currentIdx < agentOrder.length) {
      const agent = agentOrder[currentIdx];
      if (doneSet.has(agent)) {
        const ready = fastMode || typingDone;
        if (ready) {
          const delay = fastMode ? 200 : 1200;
          const timer = setTimeout(() => setCurrentIdx(prev => prev + 1), delay);
          return () => clearTimeout(timer);
        }
      }
    }
  }, [currentIdx, agentOrder, doneSet, typingDone, fastMode]);

  // Narrative for synthesis (from manager synthesis phase + synthesis node)
  const synthesisNarrative = useMemo(() => {
    if (!showSynthesis) return "";
    return events
      .filter(e =>
        (e.node_id === "synthesis" && e.narrative) ||
        (e.node_id === "manager" && e.metadata?.phase === "synthesis" && e.narrative)
      )
      .map(e => e.narrative)
      .join("\n\n");
  }, [events, showSynthesis]);

  const { displayed: synthText, isComplete: synthDone } = useTypewriter(
    synthesisNarrative && !isSynthesisDone ? synthesisNarrative : "",
    30
  );

  // Current tool name for active agent
  const currentTool = useMemo(() => {
    if (!activeAgent) return "";
    const agentEvts = events.filter(e => e.node_id === activeAgent);
    for (let i = agentEvts.length - 1; i >= 0; i--) {
      const tool = agentEvts[i].metadata?.tool_name;
      if (tool) return tool as string;
    }
    return "";
  }, [events, activeAgent]);

  if (events.length === 0) return <ObservationWelcome />;

  const hasAudit = agentOrder.length > 0;

  return (
    <div className="flex flex-col items-center gap-4 py-8 max-w-4xl mx-auto w-full relative">
      {hasAudit && <PhaseDots currentPhase={visualPhase} />}

      <div className="w-full flex flex-col items-center gap-0 relative px-2">
        <AgentStatusBar icon={<Icons.Brain />} title="Manager Agent" subtitle="Strategic Planning" />

        {agentOrder.map((agent, idx) => {
          const display = agentDisplay[agent];
          const isDone = doneSet.has(agent);
          const isActive = idx === currentIdx;
          const isCollapsed = idx < currentIdx || (isActive && isDone) || (fastMode && isDone);

          return (
            <React.Fragment key={agent}>
              <ConnectorLine />
              {isCollapsed ? (
                <AgentStatusBar
                  icon={display?.icon || <Icons.Globe />}
                  title={display?.title || agent.replace(/_/g, " ")}
                  subtitle={display?.subtitle || agent}
                />
              ) : isActive ? (
                <WorkflowNode
                  title={display?.title || agent.replace(/_/g, " ")}
                  subtitle={display?.subtitle || agent}
                  status={isDone ? "DONE" : "EXECUTING"}
                  icon={display?.icon || <Icons.Globe />}
                  typedText={fastMode ? undefined : typedText}
                  isTyping={!typingDone && !fastMode}
                  toolName={currentTool}
                />
              ) : null}
            </React.Fragment>
          );
        })}

        {hasAudit && showSynthesis && (
          <React.Fragment>
            <ConnectorLine />
            <WorkflowNode
              title="Final Synthesis"
              subtitle="Manager Agent"
              status={isSynthesisDone ? "DONE" : "EXECUTING"}
              icon={<Icons.FileText />}
              typedText={fastMode ? undefined : (synthText || undefined)}
              isTyping={!synthDone && !isSynthesisDone}
              log={isSynthesisDone ? "✅ Laporan audit berhasil disusun dan siap ditinjau." : ""}
            />
          </React.Fragment>
        )}
      </div>
    </div>
  );
}

// ── Workflow Node ──
function WorkflowNode({ title, subtitle, status, icon, log, typedText, isTyping, toolName }: {
  title: string,
  subtitle: string,
  status: "PENDING" | "EXECUTING" | "DONE" | "SKIP",
  icon: React.ReactNode,
  log?: string,
  typedText?: string,
  isTyping?: boolean,
  toolName?: string
}) {
  const isRunning = status === "EXECUTING";
  const isDone = status === "DONE";
  const isSkip = status === "SKIP";
  const statusLabel = isRunning ? "Memproses" : isDone ? "Selesai" : isSkip ? "Dilewati" : "Menunggu";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className={`relative w-full p-6 rounded-2xl border transition-all duration-500 overflow-hidden ${
        isRunning
          ? "bg-[var(--pemali-surface)] border-[var(--pemali-accent)] shadow-2xl shadow-[var(--pemali-accent)]/5 z-20"
          : isDone
          ? "bg-[var(--pemali-surface)] border-[var(--pemali-border)] opacity-100"
          : "bg-transparent border-dashed border-[var(--pemali-border)] opacity-30"
      }`}
    >
      {/* Glow effect for running */}
      {isRunning && (
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-[var(--pemali-accent)]/5 rounded-full blur-3xl pointer-events-none" />
      )}

      <div className="flex items-start gap-5 relative z-10">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 transition-all duration-500 ${
          isRunning
            ? "bg-[var(--pemali-accent)] text-white shadow-lg shadow-[var(--pemali-accent)]/20"
            : isDone
            ? "bg-[var(--pemali-accent)]/10 text-[var(--pemali-accent)]"
            : "bg-zinc-800 text-zinc-500"
        }`}>
          {isRunning ? (
            <motion.div
              animate={{ scale: [1, 1.15, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              {icon}
            </motion.div>
          ) : icon}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <h4 className="text-[15px] font-bold text-[var(--pemali-text-primary)]">{title}</h4>
            <div className={`text-[9px] px-2.5 py-0.5 rounded-full font-mono uppercase tracking-tighter border ${
              isRunning
                ? "border-[var(--pemali-accent)]/50 text-[var(--pemali-accent)] bg-[var(--pemali-accent)]/5"
                : isDone
                ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/5"
                : "border-zinc-700 text-zinc-600"
            }`}>
              {statusLabel}
            </div>
          </div>
          <p className="text-[11px] text-[var(--pemali-text-muted)] font-mono uppercase tracking-wider">{subtitle}</p>

          {/* Tool name */}
          {toolName && isRunning && (
            <div className="flex items-center gap-1.5 mt-2">
              <Icons.Zap />
              <span className="text-[11px] text-[var(--pemali-accent)] font-mono">{toolName}</span>
            </div>
          )}

          {/* Typewriter thinking text */}
          <AnimatePresence>
            {typedText !== undefined && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="mt-4 pt-4 border-t border-[var(--pemali-border)]/50"
              >
                <div className="flex items-center gap-2 mb-2">
                  <div className="text-[10px] text-[var(--pemali-accent)] font-bold uppercase tracking-widest flex items-center gap-1.5">
                    <Icons.Clock />
                    {isTyping ? "Alur Berpikir" : "Log Berpikir"}
                  </div>
                  {isTyping && (
                    <div className="w-2 h-2 rounded-full bg-[var(--pemali-accent)] animate-pulse" />
                  )}
                </div>
                <div className="max-h-64 overflow-y-auto rounded-lg bg-black/10 p-4 font-mono text-[12px] text-[var(--pemali-text-primary)] leading-relaxed whitespace-pre-wrap scrollbar-thin">
                  <AnimatePresence mode="popLayout">
                    {typedText ? (
                      <motion.span
                        key={typedText.length > 50 ? "typing" : "empty"}
                        initial={{ opacity: 0.6 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.4 }}
                      >
                        {typedText}
                      </motion.span>
                    ) : (
                      <motion.span
                        key="placeholder"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                      >
                        {isTyping ? "Menunggu proses..." : "Tidak ada data berpikir"}
                      </motion.span>
                    )}
                  </AnimatePresence>
                  {isTyping && <span className="animate-pulse text-[var(--pemali-accent)] ml-0.5">▊</span>}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Legacy log section */}
          {typedText === undefined && (isRunning || (isDone && log)) && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              className="mt-4 pt-4 border-t border-[var(--pemali-border)]/50"
            >
              <div className="flex items-center gap-2 mb-2">
                <div className="text-[10px] text-[var(--pemali-accent)] font-bold uppercase tracking-widest flex items-center gap-1.5">
                  <Icons.Clock />
                  Log Berpikir
                </div>
              </div>
              <div className="text-[12px] text-[var(--pemali-text-secondary)] leading-relaxed">
                {log}
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* Connector Dot */}
      <div className={`absolute top-1/2 left-[-12px] md:left-1/2 md:-translate-x-1/2 w-3 h-3 rounded-full border-2 border-[var(--pemali-bg)] z-30 transition-all duration-700 hidden md:block ${
        isRunning
          ? "bg-[var(--pemali-accent)] scale-150 shadow-lg shadow-[var(--pemali-accent)]/50"
          : isDone
          ? "bg-emerald-500"
          : "bg-[var(--pemali-border)]"
      }`} />
    </motion.div>
  );
}

import { type Session } from "@/lib/dashboard";

// ── Sidebar ──
interface SidebarProps {
  sessions: Session[];
  onNewAudit: () => void;
  onSelectSession: (id: string) => void;
  activeSessionId: string;
  isOpen: boolean;
  onToggle: () => void;
}

export function Sidebar({
  sessions,
  onNewAudit,
  onSelectSession,
  activeSessionId,
  isOpen,
  onToggle,
}: SidebarProps) {
  return (
    <motion.div
      initial={false}
      animate={{ width: isOpen ? 280 : 0, opacity: isOpen ? 1 : 0 }}
      className="h-full border-r border-[var(--pemali-border)] bg-[var(--pemali-surface)] flex flex-col overflow-hidden relative"
    >
      <div className="p-6 border-b border-[var(--pemali-border)] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-[var(--pemali-accent)] flex items-center justify-center text-white shadow-lg">
            <img src="/logo.png" alt="PEMALI" className="w-5 h-5 object-contain" />
          </div>
          <span className="text-[15px] font-bold tracking-tight text-[var(--pemali-text-primary)]">PEMALI</span>
        </div>
        <button onClick={onToggle} className="p-1.5 hover:bg-[var(--pemali-bg)] rounded-md text-[var(--pemali-text-muted)]">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/></svg>
        </button>
      </div>

      <div className="p-4">
        <button onClick={onNewAudit} className="w-full py-2.5 px-4 bg-[var(--pemali-accent)] text-white rounded-xl text-[13px] font-semibold flex items-center justify-center gap-2 shadow-lg transition-transform active:scale-95">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Audit Baru
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 scrollbar-none">
        <div className="text-[10px] font-bold text-[var(--pemali-text-muted)] uppercase tracking-widest p-4 pb-2">Sesi Terbaru</div>
        <div className="flex flex-col gap-1">
          {sessions.map((s: any) => (
            <button
              key={s.id}
              onClick={() => onSelectSession(s.id)}
              className={`w-full text-left px-4 py-3 rounded-xl transition-all group ${
                activeSessionId === s.id ? "bg-[var(--pemali-accent)]/10 text-[var(--pemali-accent)]" : "hover:bg-[var(--pemali-bg)] text-[var(--pemali-text-secondary)]"
              }`}
            >
              <div className="text-[13px] font-medium truncate mb-1">{s.title || s.id}</div>
              <div className="text-[9px] font-mono opacity-50 uppercase">
                {s.last_activity ? new Date(s.last_activity).toLocaleDateString("id-ID", {
                  day: "2-digit",
                  month: "short",
                  year: "numeric"
                }) : ""}
              </div>
            </button>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

// ── Final Report ──
export function FinalReport({ content, isLoading }: { content: string; isLoading?: boolean }) {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="max-w-4xl mx-auto w-full py-12">
      <div className="bg-[var(--pemali-surface)] border border-[var(--pemali-border)] rounded-[32px] p-12 shadow-2xl relative overflow-hidden">
        {/* Paper texture/gradient */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-[var(--pemali-accent)]/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />

        <div className="flex items-start justify-between mb-16 relative z-10">
          <div>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-full bg-[var(--pemali-accent)] flex items-center justify-center text-white">
                <img src="/logo.png" alt="PEMALI" className="w-6 h-6 object-contain" />
              </div>
              <div className="text-[11px] font-bold text-[var(--pemali-accent)] uppercase tracking-[0.3em]">Laporan Audit Lingkungan</div>
            </div>
            <h1 className="text-4xl font-semibold text-[var(--pemali-text-primary)] mb-2 tracking-tight" style={{ fontFamily: "'Lora', serif" }}>
              Analisis Dampak & Rekomendasi
            </h1>
          </div>
          <div className="text-right">
            <div className="text-[12px] font-bold text-[var(--pemali-text-primary)] mb-1">PEMALI CORE v2.0</div>
            <div className="text-[11px] text-[var(--pemali-text-muted)] font-mono uppercase mb-4 tracking-widest">Unit Analisis Otonom</div>
            <div className="inline-block px-3 py-1 rounded-full border border-[var(--pemali-border)] text-[10px] font-bold text-[var(--pemali-text-muted)] uppercase tracking-tighter">
              {new Date().toLocaleDateString("id-ID", { day: '2-digit', month: 'long', year: 'numeric' })}
            </div>
          </div>
        </div>

        <div className="prose max-w-none prose-headings:font-serif prose-headings:font-medium prose-p:text-[var(--pemali-text-secondary)] prose-p:leading-[1.8] prose-p:text-[16px] prose-table:border-collapse prose-table:w-full prose-th:border-b prose-th:border-[var(--pemali-border)] prose-th:py-2 prose-th:text-left prose-th:font-semibold prose-th:text-[var(--pemali-text-primary)] prose-td:border-b prose-td:border-[var(--pemali-border)]/50 prose-td:py-2 prose-td:text-[var(--pemali-text-secondary)]">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>

        {isLoading && (
          <div className="mt-12 pt-12 border-t border-[var(--pemali-border)]/50">
            <div className="flex items-center gap-4 text-[var(--pemali-text-muted)]">
              <div className="w-5 h-5 border-2 border-[var(--pemali-accent)] border-t-transparent rounded-full animate-spin" />
              <span className="text-[13px]">Menyinkronkan data multi-agent ke dalam sintesis final...</span>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
