"use client";

/* Direction: Dark Terminal Observatory — Status Bar */

import { motion } from "framer-motion";
import { useTelemetryStore } from "@/stores/telemetryStore";

interface SwarmStatusBarProps {
  state: string;
  phase: string | null;
  confidence: number | null;
  runningTaskId: string | null;
}

const STATE_META: Record<string, { label: string; color: string }> = {
  THINKING:  { label: "Thinking",  color: "var(--state-thinking)" },
  SPAWNING:  { label: "Spawning",  color: "var(--state-spawning)" },
  EXECUTING: { label: "Executing", color: "var(--state-executing)" },
  DONE:      { label: "Done",      color: "var(--state-complete)" },
  ERROR:     { label: "Error",     color: "var(--state-error)" },
  IDLE:      { label: "Idle",      color: "var(--pemali-text-muted)" },
};

export default function SwarmStatusBar({ state, phase, confidence, runningTaskId }: SwarmStatusBarProps) {
  const isConnected = useTelemetryStore((s) => s.isConnected);
  const eventCount = useTelemetryStore((s) => s.events.length);

  const meta = STATE_META[state] || STATE_META.IDLE;
  const isActive = state !== "DONE" && state !== "ERROR" && state !== "IDLE";

  return (
    <div className="flex items-center justify-between px-0 py-2 border-b border-[var(--pemali-border)]">
      {/* Left: state */}
      <div className="flex items-center gap-2">
        <motion.span
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: meta.color }}
          animate={isActive ? { opacity: [0.3, 1, 0.3], scale: [1, 1.15, 1] } : {}}
          transition={{ duration: 1.6, repeat: isActive ? Infinity : 0, ease: "easeInOut" }}
        />
        <span className="text-[13px] font-[500] font-sans text-[var(--pemali-text-primary)]">
          {runningTaskId ? `#${runningTaskId}` : "Agent Otak"}
        </span>
        <span
          className="text-[11px] font-mono font-[500] px-1.5 py-0.5 rounded"
          style={{ backgroundColor: `${meta.color}18`, color: meta.color }}
        >
          {meta.label}
        </span>
        {phase && (
          <span className="text-[11px] font-mono text-[var(--pemali-text-muted)]">
            {phase}
          </span>
        )}
      </div>

      {/* Right: metrics */}
      <div className="flex items-center gap-3 text-[11px] font-mono text-[var(--pemali-text-muted)]">
        {confidence != null && (
          <span className="tabular-nums">
            conf:{confidence}/10
          </span>
        )}
        <span className="tabular-nums">
          {eventCount} evts
        </span>
        <span className="flex items-center gap-1">
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: isConnected ? "var(--state-complete)" : "var(--state-error)" }}
          />
          {isConnected ? "live" : "off"}
        </span>
      </div>
    </div>
  );
}
