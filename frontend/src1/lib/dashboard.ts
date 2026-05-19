/* Direction: Anthropic Terminal — Warm Editorial Control Room */

export type NodeType = "Manager" | "SubAgent" | "Module";
export type NodeState =
  | "IDLE"
  | "THINKING"
  | "SPAWNING"
  | "EXECUTING"
  | "DONE"
  | "ERROR";

export interface TelemetryEvent {
  trace_id: string;
  node_id: string;
  node_type: NodeType;
  state: NodeState;
  narrative: string;
  timestamp: number;
  metadata?: {
    tool_name?: string;
    duration_ms?: number;
    rag_sources?: string[];
    phase?: string;
    status?: number;
    error?: string;
    type?: string;
    agent?: string;
    phase_step?: string;
    [key: string]: unknown;
  } | null;
}

export interface TokenEvent {
  node_id: string;
  content: string;
}

export interface Session {
  id: string;
  title?: string;
  label?: string;
  last_activity?: string;
  ts?: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  nodeId?: string;
  ts: number;
}

// ── Design Tokens (mirror globals.css) ──
export const C = {
  bg: "var(--pemali-bg)",
  surface: "var(--pemali-surface)",
  border: "var(--pemali-border)",
  text: "var(--pemali-text-primary)",
  textSec: "var(--pemali-text-secondary)",
  textMuted: "var(--pemali-text-muted)",
  accent: "var(--pemali-accent)",
  thinking: "var(--state-thinking)",
  spawning: "var(--state-spawning)",
  executing: "var(--state-executing)",
  error: "var(--state-error)",
  complete: "var(--state-complete)",
} as const;

export const STATE_COLOR: Record<NodeState, string> = {
  IDLE: C.textMuted,
  THINKING: C.thinking,
  SPAWNING: C.spawning,
  EXECUTING: C.executing,
  ERROR: C.error,
  DONE: C.complete,
};

export const STATE_LABEL: Record<NodeState, string> = {
  IDLE: "idle",
  THINKING: "thinking",
  SPAWNING: "spawning",
  EXECUTING: "executing",
  DONE: "done",
  ERROR: "error",
};

// ── Utils ──
export function fmtTime(ts: number) {
  return new Date(ts * 1000).toLocaleTimeString("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "Asia/Makassar",
  });
}

export function shortId(id: string) {
  if (!id) return "";
  return id.replace(/_agent$/, "").replace(/_/g, " ");
}

// ── Phase Pipeline ──
export const PHASE_LABEL: Record<string, string> = {
  planning: "Planning",
  execute: "Execute",
  validate: "Validate",
  synthesis: "Synthesis",
  done: "Done",
};

export const PHASE_ORDER = ["planning", "execute", "validate", "synthesis", "done"];

export interface PhaseSegment {
  phase: string;
  label: string;
  step: string;
  narrative: string;
  metadata: TelemetryEvent["metadata"];
}

export function extractPhases(events: TelemetryEvent[]): PhaseSegment[] {
  const managerEvents = events.filter(
    (e) => e.node_id === "manager" && e.metadata?.phase
  );
  const phaseMap = new Map<string, PhaseSegment>();
  for (const ev of managerEvents) {
    const phase = ev.metadata!.phase as string;
    const step = (ev.metadata!.phase_step as string) || phase;
    if (phase === "validate" && step === "re-spawn") {
      const agent = (ev.metadata!.agent as string) || "unknown";
      const label = `Execute(${agent.replace("_agent", "")})`;
      phaseMap.set(`execute-${agent}-${ev.timestamp}`, {
        phase: "execute",
        label,
        step: "re-spawn",
        narrative: ev.narrative,
        metadata: ev.metadata,
      });
      phaseMap.set(`${phase}-${step}`, {
        phase,
        label: PHASE_LABEL[phase] || phase,
        step,
        narrative: ev.narrative,
        metadata: ev.metadata,
      });
    } else {
      const key =
        phase === "execute" && step === "re-spawn"
          ? `${phase}-re-spawn-${ev.timestamp}`
          : `${phase}-${step}`;
      if (
        !phaseMap.has(key) ||
        step === "valid" ||
        step === "complete" ||
        phase === "done"
      ) {
        phaseMap.set(key, {
          phase,
          label: PHASE_LABEL[phase] || phase,
          step,
          narrative: ev.narrative,
          metadata: ev.metadata,
        });
      }
    }
  }
  return Array.from(phaseMap.values());
}

// ── DAG Plan Extraction ──
export interface DagPlan {
  task_id: string;
  agent: string;
  intent: string;
  depends_on: string[];
}

export function extractDagFromPlan(events: TelemetryEvent[]): {
  agents: string[];
  tasks: DagPlan[];
} {
  const planEvent = events.find(
    (e) => e.node_id === "manager" && e.metadata?.phase_step === "plan"
  );

  if (planEvent?.metadata?.plan) {
    const tasks = planEvent.metadata.plan as DagPlan[];
    const sorted: DagPlan[] = [];
    const visited = new Set<string>();

    function visit(taskId: string) {
      if (visited.has(taskId)) return;
      visited.add(taskId);
      const task = tasks.find((t) => t.task_id === taskId);
      if (!task) return;
      for (const dep of task.depends_on) {
        visit(dep);
      }
      sorted.push(task);
    }

    for (const task of tasks) {
      visit(task.task_id);
    }

    const agents = [...new Set(sorted.map((t) => t.agent))];
    return { agents, tasks: sorted };
  }

  // Fallback: extract unique agent node_ids in first-seen order (history mode)
  const knownAgents = ["geo_agent", "water_agent", "fire_agent", "osint_agent", "scheduler_agent"];
  const seen: string[] = [];
  for (const e of events) {
    if (e.node_id && e.node_id !== "manager" && e.node_id !== "synthesis" && e.node_id !== "system") {
      if (!seen.includes(e.node_id) && knownAgents.includes(e.node_id)) {
        seen.push(e.node_id);
      }
    }
  }
  return { agents: seen, tasks: [] };
}

export function computeProgress(events: TelemetryEvent[]) {
  const agentEvents = events.filter(
    (e) => e.node_type !== "Module" && e.state !== "IDLE"
  );
  const doneCount = agentEvents.filter(
    (e) => e.state === "DONE" && e.node_id !== "manager"
  ).length;
  const managerPhases = events.filter(
    (e) => e.node_id === "manager" && e.metadata?.phase
  ).length;
  const total = Math.max(managerPhases + doneCount, 1);
  const current = Math.min(managerPhases, total);
  return { current, total };
}
