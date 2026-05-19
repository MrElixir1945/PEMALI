"use client";

/* Direction: Anthropic Terminal — Dev Module Data Inspector */

import React, { useMemo, useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTelemetryStore } from "@/stores/telemetryStore";
const stateColor: Record<string, string> = {
  DONE: "var(--state-complete)",
  ERROR: "var(--state-error)",
  EXECUTING: "var(--state-executing)",
  THINKING: "var(--state-thinking)",
  SPAWNING: "var(--state-spawning)",
};

function fmtTime(ts: number) {
  return new Date(ts * 1000).toLocaleTimeString("id-ID", {
    hour: "2-digit", minute: "2-digit", second: "2-digit",
    timeZone: "Asia/Makassar",
  });
}

function fmtDateTime(ts: number) {
  return new Date(ts * 1000).toLocaleString("id-ID", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit",
    timeZone: "Asia/Makassar",
  });
}

function CollapsibleJson({ data, label }: { data: unknown; label: string }) {
  const [open, setOpen] = useState(false);
  const jsonStr = useMemo(() => {
    try { return JSON.stringify(data, null, 2); } catch { return String(data); }
  }, [data]);

  return (
    <div className="border border-[var(--pemali-border)] rounded-md overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-1.5 text-[11px] font-mono text-[var(--pemali-text-muted)] hover:text-[var(--pemali-text-secondary)] transition-colors bg-[var(--pemali-surface)]"
      >
        <span className="text-[10px]">{open ? "▾" : "▸"}</span>
        <span>{label}</span>
        <span className="text-[10px] text-[var(--pemali-text-muted)] ml-auto">
          {jsonStr.length.toLocaleString()}b
        </span>
      </button>
      <AnimatePresence>
        {open && (
          <motion.pre
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="text-[11px] font-mono text-[var(--pemali-text-secondary)] leading-relaxed overflow-x-auto whitespace-pre-wrap p-3 m-0 max-h-[400px] overflow-y-auto"
          >
            {jsonStr}
          </motion.pre>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function ModuleOutputDevPanel() {
  const events = useTelemetryStore((s) => s.events);
  const isConnected = useTelemetryStore((s) => s.isConnected);
  const [filter, setFilter] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const listRef = useRef<HTMLDivElement>(null);

  const moduleEvents = useMemo(() => {
    return events.filter((e) => e.node_type === "Module");
  }, [events]);

  const eventTypeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    events.forEach((e) => {
      counts[e.node_type] = (counts[e.node_type] || 0) + 1;
    });
    return counts;
  }, [events]);

  const toolNames = useMemo(() => {
    return [...new Set(moduleEvents.map((e) => e.metadata?.tool_name as string).filter(Boolean))].sort();
  }, [moduleEvents]);

  const filtered = useMemo(() => {
    let f = moduleEvents;
    if (filter) f = f.filter((e) => e.metadata?.tool_name === filter);
    if (stateFilter) f = f.filter((e) => e.state === stateFilter);
    return f;
  }, [moduleEvents, filter, stateFilter]);

  useEffect(() => {
    if (autoScroll && listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [filtered.length, autoScroll]);

  return (
    <div className="space-y-4">
      {/* Debug stats row */}
      <div className="space-y-1 text-[10px] font-mono text-[var(--pemali-text-muted)]">
        <div className="flex items-center gap-3">
          <span className={isConnected ? "text-[var(--state-complete)]" : "text-[var(--state-error)]"}>
            SSE: {isConnected ? "connected" : "disconnected"}
          </span>
          <span>Total events in store: {events.length}</span>
          <span>Module events: {moduleEvents.length}</span>
        </div>
        <div className="flex items-center gap-3">
          <span>Manager: {eventTypeCounts.Manager || 0}</span>
          <span>SubAgent: {eventTypeCounts.SubAgent || 0}</span>
          <span>Module: {eventTypeCounts.Module || 0}</span>
          <span>with raw_payload: {moduleEvents.filter(e => e.metadata?.raw_payload).length}</span>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-[11px] font-mono text-[var(--pemali-text-muted)] uppercase tracking-wider">
          Tampil: {filtered.length}
        </span>

        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="text-[11px] font-mono px-2 py-1 rounded border border-[var(--pemali-border)] bg-[var(--pemali-surface)] text-[var(--pemali-text-secondary)] outline-none focus:border-[var(--pemali-accent)] transition-colors"
        >
          <option value="">Semua Modul</option>
          {toolNames.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        <select
          value={stateFilter}
          onChange={(e) => setStateFilter(e.target.value)}
          className="text-[11px] font-mono px-2 py-1 rounded border border-[var(--pemali-border)] bg-[var(--pemali-surface)] text-[var(--pemali-text-secondary)] outline-none focus:border-[var(--pemali-accent)] transition-colors"
        >
          <option value="">Semua State</option>
          <option value="DONE">DONE</option>
          <option value="ERROR">ERROR</option>
          <option value="EXECUTING">EXECUTING</option>
          <option value="THINKING">THINKING</option>
        </select>

        <label className="flex items-center gap-1.5 text-[11px] font-mono text-[var(--pemali-text-muted)] cursor-pointer">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
            className="accent-[var(--pemali-accent)]"
          />
          Auto-scroll
        </label>
      </div>

      {/* Event list */}
      <div
        ref={listRef}
        className="space-y-2 max-h-[70vh] overflow-y-auto pr-1"
      >
        <AnimatePresence>
          {filtered.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-12 text-[13px] text-[var(--pemali-text-muted)]"
            >
              Menunggu data module dari SSE...
            </motion.div>
          )}
          {filtered.map((event, i) => {
            const meta = event.metadata || {};
            const toolName = (meta.tool_name as string) || event.node_id;
            const state = event.state;
            const sColor = stateColor[state] || "var(--pemali-text-muted)";
            const hasPayload = !!meta.raw_payload;
            const narrative = event.narrative;

            return (
              <motion.div
                key={`${event.timestamp}-${event.node_id}-${i}`}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.25, ease: [0.0, 0.0, 0.2, 1] }}
                className="border border-[var(--pemali-border)] rounded-lg bg-[var(--pemali-surface)] overflow-hidden"
              >
                <div className="px-3 py-2 flex items-center gap-3">
                  <span className="text-[10px] font-mono text-[var(--pemali-text-muted)] tabular-nums">
                    {fmtDateTime(event.timestamp)}
                  </span>
                  <span className="text-[12px] font-mono font-[500] text-[var(--pemali-text-primary)]">
                    {toolName}
                  </span>
                  <span
                    className="text-[10px] font-mono px-1.5 py-0.5 rounded border"
                    style={{ color: sColor, borderColor: `${sColor}40`, backgroundColor: `${sColor}12` }}
                  >
                    {state}
                  </span>
                </div>

                {narrative && (
                  <div className="px-3 pb-1 text-[11px] text-[var(--pemali-text-secondary)] leading-relaxed italic">
                    {narrative}
                  </div>
                )}

                {(meta.agent_hint as string) ? (
                  <div className="px-3 pb-1.5 text-[11px] text-[var(--pemali-text-muted)] leading-relaxed font-mono border-b border-[var(--pemali-border)]">
                    agent_hint: {meta.agent_hint as string}
                  </div>
                ) : null}

                <div className="px-3 pb-2 pt-1.5">
                  {hasPayload ? (
                    <CollapsibleJson data={meta.raw_payload} label="raw_payload" />
                  ) : (
                    <div className="text-[10px] font-mono text-[var(--pemali-text-muted)] italic">
                      Tidak ada raw_payload — backend belum restart atau module belum selesai.
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
