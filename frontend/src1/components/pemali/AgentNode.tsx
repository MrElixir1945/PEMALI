"use client";

import { Bot, Cpu, Wrench, Loader2, CheckCircle, XCircle, Zap } from "lucide-react";
import type { TelemetryEvent } from "@/stores/telemetryStore";

export interface AgentNodeData {
  id: string;
  label: string;
  nodeType: "Manager" | "SubAgent" | "Module";
  state: string;
  narrative: string;
  metadata?: TelemetryEvent["metadata"];
  x: number;
  y: number;
  width: number;
  height: number;
}

const stateColors: Record<string, string> = {
  IDLE: "#6B6558",
  THINKING: "#CC785C",
  SPAWNING: "#8A9AA8",
  EXECUTING: "#8BA888",
  DONE: "#90B898",
  ERROR: "#B87870",
};

const nodeTypeIcon: Record<string, React.ElementType> = {
  Manager: Bot,
  SubAgent: Cpu,
  Module: Wrench,
};

export default function AgentNode({
  node,
  isSelected,
  onClick,
}: {
  node: AgentNodeData;
  isSelected: boolean;
  onClick: () => void;
}) {
  const color = stateColors[node.state] || stateColors.IDLE;
  const Icon = nodeTypeIcon[node.nodeType] || Cpu;
  const isRunning = node.state === "THINKING" || node.state === "EXECUTING" || node.state === "SPAWNING";

  return (
    <div
      onClick={onClick}
      style={{
        position: "absolute",
        left: node.x,
        top: node.y,
        width: node.width,
        minHeight: node.height,
        borderColor: color,
        borderWidth: isSelected ? 2 : 1,
        backgroundColor: `${color}10`,
      }}
      className="rounded-lg cursor-pointer transition-all hover:brightness-110 flex flex-col"
    >
      <div className="flex items-center gap-2 px-3 py-2 border-b" style={{ borderColor: `${color}30` }}>
        <div
          className="w-6 h-6 rounded flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: `${color}20` }}
        >
          {isRunning ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" style={{ color }} />
          ) : node.state === "DONE" ? (
            <CheckCircle className="w-3.5 h-3.5" style={{ color }} />
          ) : node.state === "ERROR" ? (
            <XCircle className="w-3.5 h-3.5" style={{ color }} />
          ) : (
            <Icon className="w-3.5 h-3.5" style={{ color }} />
          )}
        </div>

        <span className="text-xs font-mono font-medium truncate" style={{ color }}>
          {node.label}
        </span>

        <span
          className="ml-auto text-[9px] font-mono px-1.5 py-0.5 rounded"
          style={{ color, backgroundColor: `${color}15`, border: `1px solid ${color}30` }}
        >
          {node.state}
        </span>
      </div>

      {node.narrative && (
        <div className="px-3 py-2 flex-1">
          <p className="text-[11px] leading-relaxed text-[var(--pemali-text-secondary)] line-clamp-3">
            {node.narrative}
          </p>
        </div>
      )}

      {node.metadata?.duration_ms !== undefined && (
        <div className="px-3 py-1 border-t flex items-center gap-1" style={{ borderColor: `${color}20` }}>
          <Zap className="w-3 h-3 text-[var(--pemali-text-muted)]" />
          <span className="text-[9px] font-mono text-[var(--pemali-text-muted)]">
            {node.metadata.duration_ms}ms
          </span>
        </div>
      )}
    </div>
  );
}
