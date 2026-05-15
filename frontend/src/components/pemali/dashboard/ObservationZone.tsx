"use client";

import React, { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import {
  C,
  STATE_COLOR,
  STATE_LABEL,
  shortId,
  extractPhases,
  computeProgress,
  PHASE_ORDER,
  type TelemetryEvent,
  type PhaseSegment,
} from "@/lib/dashboard";

// ═══════════════════════════════════════════════════════════
// AGENT AREA — kombinasi Phase/Progress + Thinking + SubAgents
// ═══════════════════════════════════════════════════════════

export function AgentArea({ events }: { events: TelemetryEvent[] }) {
  const phases = useMemo(() => extractPhases(events), [events]);
  const lastPhase = phases[phases.length - 1];
  const currentPhase = lastPhase?.phase ?? "";

  const latestThinking = useMemo(() => {
    const thinking = events.filter(
      (e) => e.node_id === "manager" && e.state === "THINKING" && e.metadata?.phase !== "synthesis"
    );
    return thinking[thinking.length - 1] ?? null;
  }, [events]);

  const progress = useMemo(() => computeProgress(events), [events]);

  if (phases.length === 0 && !latestThinking) {
    return (
      <div className="bg-[var(--pemali-surface)] border border-[var(--pemali-border)] rounded-xl p-5 flex items-center justify-center text-[var(--pemali-text-muted)] text-xs min-h-[120px]">
        <span>Menunggu instruksi audit...</span>
      </div>
    );
  }

  return (
    <div className="bg-[var(--pemali-surface)] border border-[var(--pemali-border)] rounded-xl min-h-[240px]">
      {/* Top row: Phase/Progress (left) + Thinking text (right) */}
      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-0 divide-y lg:divide-y-0 lg:divide-x divide-[var(--pemali-border)]">
        {/* LEFT — Phase & Progress */}
        <div className="p-4 flex flex-col justify-center gap-3">
          <div className="flex items-center gap-2">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--pemali-accent)" strokeWidth="2">
              <circle cx="12" cy="8" r="4" />
              <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
            </svg>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--pemali-text-primary)]">
              Manager
            </span>
            <span
              className="ml-auto text-[10px] font-semibold uppercase tracking-wide rounded-full px-2 py-0.5"
              style={{ color: C.accent, background: "var(--pemali-accent-dim)" }}
            >
              {currentPhase || "idle"}
            </span>
          </div>

          {phases.length > 0 && <PhaseChain phases={phases} currentPhase={currentPhase} />}
          <ProgressBar current={progress.current} total={progress.total} />
        </div>

        {/* RIGHT — Thinking narrative */}
        <div className="p-4 flex items-start">
          <AnimatePresence mode="wait">
            {latestThinking ? (
              <motion.div
                key={latestThinking.narrative}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.35, ease: [0.0, 0.0, 0.2, 1] }}
                className="text-[13px] text-[var(--pemali-text-secondary)] leading-relaxed"
              >
                {latestThinking.narrative}
              </motion.div>
            ) : (
              <span className="text-xs text-[var(--pemali-text-muted)] italic">
                Manager sedang merencanakan alur audit...
              </span>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* BOTTOM — SubAgent cards */}
      <div className="border-t border-[var(--pemali-border)] p-3">
        <SubAgentGrid events={events} />
      </div>
    </div>
  );
}

// ── PhaseChain ──
function PhaseChain({ phases, currentPhase }: { phases: PhaseSegment[]; currentPhase: string }) {
  const unique = phases.reduce<PhaseSegment[]>((acc, p) => {
    const exists = acc.find((x) => x.label === p.label);
    if (!exists) acc.push(p);
    else if (p.phase === currentPhase) {
      const idx = acc.indexOf(exists);
      acc[idx] = p;
    }
    return acc;
  }, []);

  return (
    <div className="flex items-center gap-1 text-[10px] font-mono overflow-x-auto pb-0.5 whitespace-nowrap scrollbar-none">
      {unique.map((p, i) => {
        const isCurrent = p.phase === currentPhase;
        const isPast = PHASE_ORDER.indexOf(p.phase) < PHASE_ORDER.indexOf(currentPhase);
        return (
          <React.Fragment key={p.label + i}>
            <span
              className="transition-colors duration-300"
              style={{
                color: isCurrent ? "var(--pemali-accent)" : isPast ? "var(--pemali-text-secondary)" : "var(--pemali-text-muted)",
                fontWeight: isCurrent ? 600 : 400,
              }}
            >
              {p.label}
            </span>
            {i < unique.length - 1 && (
              <span className="text-[9px] text-[var(--pemali-text-muted)]">
                {isPast || isCurrent ? "●──○" : "○──○"}
              </span>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ── ProgressBar ──
function ProgressBar({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-1.5 text-[10px] font-mono text-[var(--pemali-text-muted)]">
      <span>
        {"●".repeat(Math.min(current, total))}
        {total - current > 0 ? "───○".repeat(total - current) : ""}
      </span>
      <span className="font-semibold text-[var(--pemali-text-secondary)]">
        Step {current}/{total}
      </span>
    </div>
  );
}

// ── SubAgentGrid ──
function SubAgentGrid({ events }: { events: TelemetryEvent[] }) {
  const agentIds = useMemo(() => {
    const ids = new Set<string>();
    for (const ev of events) {
      if (ev.node_type === "SubAgent" && ev.node_id !== "manager") {
        ids.add(ev.node_id);
      }
    }
    return Array.from(ids);
  }, [events]);

  if (agentIds.length === 0) {
    const hasManager = events.some((e) => e.node_id === "manager");
    if (!hasManager) return null;
    return (
      <p className="text-[11px] text-[var(--pemali-text-muted)] text-center py-2">
        Menunggu agent spawn...
      </p>
    );
  }

  return (
    <div className="flex gap-2.5 overflow-x-auto pb-1 scrollbar-thin">
      {agentIds.map((id) => (
        <SubAgentCard key={id} agentId={id} events={events} />
      ))}
    </div>
  );
}

// ── SubAgentCard ──
function SubAgentCard({ agentId, events }: { agentId: string; events: TelemetryEvent[] }) {
  const agentEvents = events.filter((e) => e.node_id === agentId);
  if (agentEvents.length === 0) return null;
  const latest = agentEvents[agentEvents.length - 1];
  const color = STATE_COLOR[latest.state];
  const thinkingEvents = agentEvents.filter((e) => e.state === "THINKING");
  const latestThinking = thinkingEvents[thinkingEvents.length - 1];

  return (
    <div
      className="min-w-[180px] max-w-[220px] shrink-0 bg-[var(--pemali-bg)] border border-[var(--pemali-border)] rounded-lg p-2.5 transition-shadow duration-300"
      style={{
        boxShadow: latest.state === "EXECUTING" ? `0 0 0 2px ${color}18` : "none",
      }}
    >
      <div className="flex items-center gap-1.5 mb-1.5">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <path d="M8 21h8M12 17v4" />
        </svg>
        <span className="text-[10px] font-semibold text-[var(--pemali-text-primary)] font-mono uppercase tracking-wider">
          {shortId(agentId)}
        </span>
        <span
          className="ml-auto text-[9px] font-semibold uppercase tracking-wide rounded-full px-1.5 py-px"
          style={{ color, background: color + "15" }}
        >
          {STATE_LABEL[latest.state]}
        </span>
      </div>

      <AnimatePresence mode="wait">
        {latestThinking && (
          <motion.p
            key={latestThinking.narrative}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.3, ease: [0.0, 0.0, 0.2, 1] }}
            className="m-0 text-[10px] text-[var(--pemali-text-secondary)] leading-snug line-clamp-2"
          >
            {latestThinking.narrative}
          </motion.p>
        )}
      </AnimatePresence>

      {latest.state === "EXECUTING" && (
        <div
          className="mt-1.5 h-0.5 rounded-full animate-shimmer"
          style={{ background: `linear-gradient(90deg, transparent, var(--state-executing), transparent)` }}
        />
      )}
      {latest.state === "DONE" && (
        <div className="mt-1.5 text-[9px] text-[var(--state-complete)] flex items-center gap-1">
          <span>✓</span> complete
        </div>
      )}
      {latest.state === "ERROR" && (
        <div className="mt-1.5 text-[9px] text-[var(--state-error)] flex items-center gap-1">
          <span>✕</span> error
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// FINAL REPORT
// ═══════════════════════════════════════════════════════════

export function FinalReport({ content, isLoading }: { content: string; isLoading?: boolean }) {
  if (!content) return null;
  return (
    <div className="bg-[var(--pemali-surface)] border border-[var(--pemali-border)] rounded-xl p-5 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[11px] font-bold text-[var(--pemali-accent)] uppercase tracking-widest">
          Laporan Final
        </span>
        {isLoading && (
          <span className="inline-block w-3 h-3 border-2 border-[var(--pemali-accent)] border-t-transparent rounded-full animate-spin" />
        )}
      </div>
      <div className="text-[13px] text-[var(--pemali-text-primary)] leading-relaxed pemali-report overflow-y-auto flex-1">
        {isLoading ? (
          <span>
            {content}
            <span className="inline-block w-0.5 h-3.5 bg-[var(--pemali-accent)] ml-0.5 align-middle animate-blink-cursor" />
          </span>
        ) : (
          <ReactMarkdown>{content}</ReactMarkdown>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// STATUS BAR
// ═══════════════════════════════════════════════════════════

export function StatusBar({
  isConnected,
  isStreaming,
  eventCount,
}: {
  isConnected: boolean;
  isStreaming: boolean;
  eventCount: number;
}) {
  return (
    <div className="h-10 bg-[var(--pemali-surface)] border-b border-[var(--pemali-border)] flex items-center px-5 gap-5 text-[11px] text-[var(--pemali-text-secondary)] font-mono">
      <span className="font-serif text-sm font-bold text-[var(--pemali-text-primary)] tracking-widest uppercase">
        Pemali
      </span>
      <span className="text-[var(--pemali-border)]">·</span>
      <span>
        <span className="text-[var(--pemali-text-muted)]">model </span>deepseek-r1
      </span>
      <span className="text-[var(--pemali-border)]">·</span>
      <span className="flex items-center gap-1.5">
        <span
          className="inline-block w-[7px] h-[7px] rounded-full"
          style={{
            background: isConnected ? "var(--state-complete)" : "var(--pemali-text-muted)",
            animation: isStreaming ? "status-pulse 1.2s infinite" : "none",
          }}
        />
        <span className="text-[var(--pemali-text-muted)]">worker </span>
        {isConnected ? "active" : "standby"}
      </span>
      <span className="text-[var(--pemali-border)]">·</span>
      <span>
        <span className="text-[var(--pemali-text-muted)]">events </span>
        {eventCount}
      </span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// SIDEBAR
// ═══════════════════════════════════════════════════════════

export function Sidebar({
  sessions,
  onNewAudit,
  onSelectSession,
  activeSessionId,
}: {
  sessions: { id: string; label: string; ts: number }[];
  onNewAudit: () => void;
  onSelectSession: (id: string) => void;
  activeSessionId: string | null;
}) {
  return (
    <div className="w-[200px] shrink-0 bg-[var(--pemali-surface)] border-r border-[var(--pemali-border)] flex flex-col p-4 gap-2">
      <button
        onClick={onNewAudit}
        className="w-full py-2 bg-[var(--pemali-accent)] text-white rounded-lg text-xs font-semibold tracking-wide cursor-pointer mb-2 hover:brightness-110 transition"
      >
        + Audit Baru
      </button>
      <div className="text-[10px] font-bold text-[var(--pemali-text-muted)] uppercase tracking-widest mb-1 pl-1.5">
        Sesi
      </div>
      {sessions.length === 0 && (
        <p className="text-[11px] text-[var(--pemali-text-muted)] pl-1.5">Belum ada sesi</p>
      )}
      {sessions.map((s) => (
        <button
          key={s.id}
          onClick={() => onSelectSession(s.id)}
          className={`w-full text-left px-2.5 py-1.5 rounded-md text-xs cursor-pointer truncate transition border ${
            activeSessionId === s.id
              ? "bg-[var(--pemali-bg)] text-[var(--pemali-text-primary)] border-[var(--pemali-border)]"
              : "bg-transparent text-[var(--pemali-text-secondary)] border-transparent hover:bg-[var(--pemali-bg)]"
          }`}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
