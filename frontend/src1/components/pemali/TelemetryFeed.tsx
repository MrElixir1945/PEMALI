"use client";

/* Direction: Dark Terminal Observatory — Live Telemetry Feed */

import { useEffect, useRef, useMemo } from "react";
import type { TelemetryEvent } from "@/lib/dashboard";

interface TelemetryFeedProps {
  events: TelemetryEvent[];
}

const STATE_STYLE: Record<string, { bg: string; text: string }> = {
  THINKING:  { bg: "var(--state-thinking)",  text: "#1A1916" },
  SPAWNING:  { bg: "var(--state-spawning)",  text: "#F5F4EF" },
  EXECUTING: { bg: "var(--state-executing)", text: "#F5F4EF" },
  DONE:      { bg: "var(--state-complete)",  text: "#1A1916" },
  ERROR:     { bg: "var(--state-error)",     text: "#F5F4EF" },
  IDLE:      { bg: "var(--pemali-text-muted)", text: "#F5F4EF" },
};

function fmtTimestamp(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: "Asia/Makassar",
  });
}

function shortNodeId(nodeId: string): string {
  return nodeId
    .replace("agent_run_", "run/")
    .replace("agent_otak", "otak")
    .replace("_monitor", "")
    .replace("_detector", "")
    .replace("_index", "")
    .replace("_search", "")
    .replace("_scheduler", "sched")
    .replace("_scanner", "")
    .slice(0, 18);
}

export default function TelemetryFeed({ events }: TelemetryFeedProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  const filtered = useMemo(() => {
    return events.slice(-100);
  }, [events]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [filtered.length]);

  if (filtered.length === 0) {
    return (
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[11px] font-mono font-[500] uppercase tracking-wider text-[var(--pemali-text-muted)]">
            Live Feed
          </span>
        </div>
        <div className="border border-[var(--pemali-border)] rounded-lg px-3 py-8 text-center bg-[var(--pemali-surface)]">
          <p className="text-[12px] font-mono text-[var(--pemali-text-muted)]">
            Menunggu event dari Agent Otak...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[11px] font-mono font-[500] uppercase tracking-wider text-[var(--pemali-text-muted)]">
          Live Feed
        </span>
        <span className="text-[11px] font-mono text-[var(--pemali-text-muted)] tabular-nums">
          {filtered.length}
        </span>
      </div>
      <div
        className="border border-[var(--pemali-border)] rounded-lg overflow-y-auto bg-[var(--pemali-surface)]"
        style={{ maxHeight: "calc(100vh - 240px)", minHeight: "320px" }}
      >
        <div className="px-3 py-1.5 space-y-0.5">
          {filtered.map((e, i) => {
            const style = STATE_STYLE[e.state] || STATE_STYLE.IDLE;
            return (
              <div
                key={`${e.timestamp}-${e.node_id}-${i}`}
                className="flex items-start gap-1.5 py-1 text-[11.5px] leading-snug hover:bg-[var(--pemali-accent-dim)] rounded-sm transition-colors group"
              >
                <span className="font-mono text-[var(--pemali-text-muted)] flex-shrink-0 w-14 tabular-nums opacity-60 group-hover:opacity-100 transition-opacity">
                  {e.timestamp ? fmtTimestamp(e.timestamp) : "--:--:--"}
                </span>
                <span className="font-mono text-[var(--pemali-text-secondary)] flex-shrink-0 w-16 truncate" title={e.node_id}>
                  {shortNodeId(e.node_id)}
                </span>
                <span
                  className="font-mono font-[500] text-[10px] px-1 rounded flex-shrink-0"
                  style={{ backgroundColor: `${style.bg}18`, color: style.bg }}
                >
                  {e.state}
                </span>
                <span className="text-[var(--pemali-text-secondary)] truncate min-w-0">
                  {e.narrative}
                </span>
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}
