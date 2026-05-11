"use client";

import { motion } from "framer-motion";
import { Cpu, Bot, Wrench, Clock } from "lucide-react";
import type { TelemetryEvent } from "@/stores/telemetryStore";

const stateConfig: Record<string, { color: string; bg: string }> = {
  THINKING: { color: "var(--state-thinking)", bg: "rgba(139,92,246,0.12)" },
  SPAWNING: { color: "var(--state-spawning)", bg: "rgba(59,130,246,0.12)" },
  EXECUTING: { color: "var(--state-executing)", bg: "rgba(16,185,129,0.12)" },
  ERROR: { color: "var(--state-error)", bg: "rgba(239,68,68,0.12)" },
  DONE: { color: "var(--state-complete)", bg: "rgba(110,231,183,0.12)" },
};

const nodeTypeIcon: Record<string, React.ElementType> = {
  Manager: Bot,
  SubAgent: Cpu,
  Module: Wrench,
};

function formatTime(ts: number) {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function NarrativeCard({ event }: { event: TelemetryEvent }) {
  const config = stateConfig[event.state] || {
    color: "var(--pemali-text-muted)",
    bg: "transparent",
  };
  const Icon = nodeTypeIcon[event.node_type] || Cpu;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.2 }}
      className="flex gap-3 group"
    >
      <div className="relative flex flex-col items-center">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 border"
          style={{
            backgroundColor: config.bg,
            borderColor: config.color,
          }}
        >
          <Icon className="w-4 h-4" style={{ color: config.color }} />
        </div>
        <div
          className="w-px flex-1 mt-1"
          style={{ backgroundColor: `${config.color}40` }}
        />
      </div>

      <div className="flex-1 min-w-0 pb-4">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-xs font-semibold text-[var(--pemali-text-primary)]">
            {event.node_type === "Module"
              ? event.node_id
              : `${event.node_type} · ${event.node_id}`}
          </span>
          <span
            className="text-[9px] font-mono px-1.5 py-0.5 rounded border"
            style={{
              color: config.color,
              borderColor: `${config.color}40`,
              backgroundColor: config.bg,
            }}
          >
            {event.state}
          </span>
          <span className="text-[9px] font-mono text-[var(--pemali-text-muted)] ml-auto">
            {formatTime(event.timestamp)}
          </span>
        </div>

        <p className="text-[13px] text-[var(--pemali-text-secondary)] leading-relaxed">
          {event.narrative}
        </p>

        {event.metadata && (
          <div className="flex items-center gap-2 mt-2">
            {event.metadata.tool_name && (
              <span className="text-[10px] font-mono text-[var(--pemali-accent)] bg-[var(--pemali-accent-dim)] px-2 py-0.5 rounded">
                {event.metadata.tool_name}
              </span>
            )}
            {event.metadata.duration_ms !== undefined && (
              <span className="text-[10px] font-mono text-[var(--pemali-text-muted)] flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {event.metadata.duration_ms}ms
              </span>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
