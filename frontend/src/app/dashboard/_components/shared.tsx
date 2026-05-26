"use client";

import type { TelemetryEvent } from "@/stores/telemetryStore";

export type NodeState = "IDLE" | "THINKING" | "SPAWNING" | "EXECUTING" | "DONE" | "ERROR";
export type ManagerPhase = "planning" | "execute" | "validate" | "synthesis" | "done";

export interface PhaseSegment {
  phase: string;
  label: string;
  step?: string;
  narrative?: string;
  metadata?: Record<string, unknown> | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

export interface SessionEntry {
  id: string;
  label: string;
  timestamp: number;
}

export const C = {
  bg: "var(--pemali-bg)",
  surface: "var(--pemali-surface)",
  white: "#FAFBFA",
  border: "var(--pemali-border)",
  borderLight: "rgba(26,25,20,0.07)",
  text: "var(--pemali-text-primary)",
  textSec: "var(--pemali-text-secondary)",
  textMuted: "var(--pemali-text-muted)",
  accent: "var(--pemali-accent)",
  accentBg: "var(--pemali-accent-dim)",
  accentBorder: "var(--pemali-border-glow)",
  thinking: "var(--state-thinking)",
  executing: "var(--state-executing)",
  executingBg: "rgba(122,154,120,0.11)",
  executingBorder: "rgba(122,154,120,0.30)",
  error: "var(--state-error)",
  errorBg: "rgba(176,112,104,0.10)",
  errorBorder: "rgba(176,112,104,0.28)",
  done: "var(--state-complete)",
  doneBg: "rgba(128,168,136,0.12)",
  doneBorder: "rgba(128,168,136,0.30)",
  synthBg: "rgba(56,130,200,0.08)",
  synthBorder: "rgba(56,130,200,0.22)",
  synthText: "#1A5090",
};

export function stateColor(state: NodeState): string {
  switch (state) {
    case "THINKING": case "SPAWNING": return C.thinking;
    case "EXECUTING": return C.executing;
    case "DONE": return C.done;
    case "ERROR": return C.error;
    default: return C.textMuted;
  }
}

export function stateBg(state: NodeState): string {
  switch (state) {
    case "THINKING": case "SPAWNING": return C.accentBg;
    case "EXECUTING": return C.executingBg;
    case "DONE": return C.doneBg;
    case "ERROR": return C.errorBg;
    default: return "transparent";
  }
}

export function stateBorder(state: NodeState): string {
  switch (state) {
    case "THINKING": case "SPAWNING": return C.accentBorder;
    case "EXECUTING": return C.executingBorder;
    case "DONE": return C.doneBorder;
    case "ERROR": return C.errorBorder;
    default: return C.border;
  }
}

export function nodeLabel(nodeId: string): string {
  const map: Record<string, string> = {
    manager: "MGR", geo_agent: "GEO", water_agent: "H\u2082O",
    fire_agent: "FIRE", osint_agent: "OSNT", scheduler_agent: "SCHED",
    mock_data_generator: "MOCK", system_scheduler: "SYS", worker_daemon: "WRKR",
  };
  return map[nodeId] ?? nodeId.slice(0, 4).toUpperCase();
}

export function nodeGlyph(nodeId: string): string {
  const map: Record<string, string> = {
    manager: "\u25C8", geo_agent: "\u25CE", water_agent: "\u25C9",
    fire_agent: "\u25C6", osint_agent: "\u25D0", scheduler_agent: "\u25D1",
  };
  return map[nodeId] ?? "\u25CB";
}

export function nodeAccentColors(nodeId: string): { bg: string; color: string } {
  const map: Record<string, { bg: string; color: string }> = {
    manager: { bg: C.accentBg, color: C.accent },
    geo_agent: { bg: C.executingBg, color: "#5A8A58" },
    water_agent: { bg: C.synthBg, color: C.synthText },
    fire_agent: { bg: C.errorBg, color: C.error },
    osint_agent: { bg: "rgba(138,149,152,0.12)", color: "#5A7A82" },
    scheduler_agent: { bg: "rgba(138,149,152,0.12)", color: "#5A7A82" },
  };
  return map[nodeId] ?? { bg: "rgba(26,25,20,0.07)", color: C.textSec };
}

export function extractPhases(events: TelemetryEvent[]): PhaseSegment[] {
  const seen: string[] = [];
  const segs: PhaseSegment[] = [];
  for (const e of events) {
    if (e.node_id !== "manager") continue;
    const phase = e.metadata?.phase as string | undefined;
    if (!phase) continue;
    const step = e.metadata?.phase_step as string | undefined;
    const agentName = e.metadata?.agent as string | undefined;
    const key = phase === "validate" && step === "re-spawn" && agentName
      ? `execute(${agentName})` : phase;
    if (!seen.includes(key)) {
      seen.push(key);
      const labels: Record<string, string> = {
        planning: "Planning", execute: "Execute", validate: "Validate",
        synthesis: "Synthesis", done: "Done",
      };
      segs.push({
        phase: key,
        label: key.startsWith("execute(") ? `Execute(${agentName})` : (labels[key] ?? key),
        step, narrative: e.narrative, metadata: e.metadata,
      });
    }
  }
  return segs;
}

export function getSubAgentIds(events: TelemetryEvent[]): string[] {
  const seen = new Set<string>();
  for (const e of events) {
    if (e.node_type === "SubAgent" && e.node_id !== "manager") seen.add(e.node_id);
  }
  return Array.from(seen);
}

export function computeProgress(events: TelemetryEvent[]): { current: number; total: number } {
  const agentEvents = events.filter((e) => e.node_type !== "Module" && e.state !== "IDLE");
  const managerPhases = events.filter((e) => e.node_id === "manager" && e.metadata?.phase).length;
  const subDone = agentEvents.filter((e) => e.state === "DONE" && e.node_id !== "manager").length;
  const total = Math.max(managerPhases + subDone, 1);
  return { current: Math.min(managerPhases, total), total };
}

export function StateBadge({ state }: { state: NodeState }) {
  return (
    <span style={{
      fontSize: 9, letterSpacing: "0.07em", fontWeight: 500,
      padding: "2px 6px", borderRadius: 4,
      background: stateBg(state), color: stateColor(state),
      border: `0.5px solid ${stateBorder(state)}`, whiteSpace: "nowrap",
    }}>
      {state}
    </span>
  );
}

export function NodeIconBadge({ nodeId, size = 20 }: { nodeId: string; size?: number }) {
  const colors = nodeAccentColors(nodeId);
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      width: size, height: size, borderRadius: Math.round(size * 0.28),
      background: colors.bg, color: colors.color,
      fontSize: Math.round(size * 0.52), flexShrink: 0,
    }}>
      {nodeGlyph(nodeId)}
    </span>
  );
}

export function ShimmerBar() {
  return (
    <div style={{
      height: 2, borderRadius: 2, width: "100%",
      background: `linear-gradient(90deg, ${C.surface} 0%, ${C.accent}55 50%, ${C.surface} 100%)`,
      backgroundSize: "200% 100%", animation: "shimmer 1.6s linear infinite",
    }} />
  );
}
