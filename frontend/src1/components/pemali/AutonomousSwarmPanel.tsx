"use client";

/* Direction: Refined Anthropic Editorial — Swarm Panel */

import React, { useEffect, useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { useTelemetryStore } from "@/stores/telemetryStore";

// ─── Anthropic palette ───
const A = {
  bg: "#F5F4EF",
  surface: "#EDEBE4",
  surfaceHover: "#E5E2DA",
  text: "#1A1916",
  text2: "#5E5A54",
  text3: "#7A7670",
  accent: "#C8A882",
  border: "rgba(26,25,22,0.08)",
  thinking: "#9B8EC4",
  executing: "#6B9E7A",
  done: "#8B9D83",
  error: "#C47E6E",
};

// ─── Types ───
interface LaporanSummary {
  id: number; title: string; priority: number; location: string;
  metadata: Record<string, unknown> | null; created_at: string;
}
interface TaskResponse { total: number; tasks: Array<{ id: number; task_type: string; priority: number; intent_description: string; execute_at: string; status: string; retries: number; last_error: string | null; created_at: string; }>; }
interface LaporanListResponse { total: number; reports: LaporanSummary[]; }
interface AgentRunState { caseId: string; title: string; priority: number; state: string; narrative: string; urgencyReason: string; }
interface CaseItem { case_id: string; title: string; priority: number; intent: string; urgency_reason: string; }
interface EvaluationData { was_decision_correct?: boolean; strategy_adjustments?: string; confidence?: number; is_first_cycle?: boolean; evaluation_failed?: boolean; }
interface ScanSummary { weather?: { avg_temp: number; max_temp: number }; fire_hotspots?: { count: number; status: string }; earthquakes?: { count_24h: number; max_mag: number }; air_quality?: { worst_aqi: number; worst_location: string }; }

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://10.10.20.254:8000";
const POLL_INTERVAL = 10000;

const fmtDate = (iso: string) => {
  if (!iso) return "";
  const d = !iso.endsWith("Z") && !iso.includes("+") ? new Date(iso + "Z") : new Date(iso);
  return d.toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Makassar" });
};

const fmtCountdown = (target: string): string => {
  const diff = new Date(target).getTime() - Date.now();
  if (diff <= 0) return "sekarang";
  const h = Math.floor(diff / 3600000), m = Math.floor((diff % 3600000) / 60000);
  return h > 0 ? `${h}j ${m}m` : `${m}m`;
};

const stateColor = (s: string) =>
  s === "EXECUTING" ? A.executing : s === "THINKING" ? A.thinking :
  s === "DONE" ? A.done : s === "ERROR" ? A.error :
  s === "SPAWNING" ? A.accent : A.text3;

// ═══════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════
export default function AutonomousSwarmPanel() {
  const router = useRouter();
  const events = useTelemetryStore((s) => s.events);
  const sseConnected = useTelemetryStore((s) => s.isConnected);

  const [lastReport, setLastReport] = useState<LaporanSummary | null>(null);
  const [history, setHistory] = useState<LaporanSummary[]>([]);
  const [pendingTask, setPendingTask] = useState<{ id: number; execute_at: string } | null>(null);
  const [runningTask, setRunningTask] = useState<{ id: number } | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // ── Derived ──
  const otakEvents = useMemo(() => events.filter((e) => e.node_id === "agent_otak"), [events]);
  const latestOtak = otakEvents[otakEvents.length - 1];
  const isLive = useMemo(() => {
    if (latestOtak && latestOtak.state !== "DONE" && latestOtak.state !== "ERROR") return true;
    if (!sseConnected && runningTask) return true;
    return false;
  }, [latestOtak, sseConnected, runningTask]);

  const planEvent = useMemo(() => {
    for (let i = events.length - 1; i >= 0; i--) {
      if (events[i].metadata?.phase === "plan" && events[i].metadata?.cases) return events[i];
    }
    return null;
  }, [events]);
  const planCases = useMemo(() => (planEvent?.metadata?.cases as CaseItem[]) || [], [planEvent]);
  const scanSummary = useMemo(() => (planEvent?.metadata?.scan_summary as ScanSummary) || null, [planEvent]);
  const evaluation = useMemo(() => {
    const e = otakEvents.find(e => e.metadata?.phase === "evaluation");
    return (e?.metadata?.evaluation as EvaluationData) || null;
  }, [otakEvents]);
  const agentRuns = useMemo(() => {
    const map = new Map<string, AgentRunState>();
    for (const e of events) {
      const caseId = e.metadata?.case_id as string | undefined;
      if (!caseId || e.node_id !== `agent_run_${caseId}`) continue;
      const ex = map.get(caseId);
      if (e.state === "SPAWNING" || !ex) {
        map.set(caseId, { caseId, title: (e.metadata?.title as string) || caseId, priority: (e.metadata?.priority as number) ?? 5, state: e.state || "IDLE", narrative: e.narrative || "", urgencyReason: (e.metadata?.urgency_reason as string) || "" });
      } else {
        map.set(caseId, { ...ex, state: e.state, narrative: e.narrative || ex.narrative });
      }
    }
    return Array.from(map.values()).sort((a, b) => b.priority - a.priority);
  }, [events]);

  const subAgentEvents = useMemo(() => events.filter(e => e.node_type === "SubAgent" || e.node_type === "Module"), [events]);
  const agentNames = useMemo(() => [...new Set(events.filter(e => e.node_type === "SubAgent").map(e => e.node_id).filter(Boolean))], [events]);

  // ── Polling ──
  const fetchData = useCallback(async () => {
    try {
      const [lr, tp, tr] = await Promise.all([
        fetch(`${BACKEND}/api/laporan?source=autonomous&limit=1`),
        fetch(`${BACKEND}/api/tasks?status=pending&type=autonomous&limit=1`),
        fetch(`${BACKEND}/api/tasks?status=running&type=autonomous`),
      ]);
      if (lr.ok) { const d: LaporanListResponse = await lr.json(); setLastReport(d.reports[0] || null); }
      if (tp.ok) { const d: TaskResponse = await tp.json(); setPendingTask(d.tasks[0] ? { id: d.tasks[0].id, execute_at: d.tasks[0].execute_at } : null); }
      if (tr.ok) { const d: TaskResponse = await tr.json(); setRunningTask(d.tasks[0] ? { id: d.tasks[0].id } : null); }
      const hr = await fetch(`${BACKEND}/api/laporan?source=autonomous&limit=10`);
      if (hr.ok) { const d: LaporanListResponse = await hr.json(); setHistory(d.reports); }
      setApiError(null);
    } catch { /* retry */ }
  }, []);
  useEffect(() => { fetchData(); const i = setInterval(fetchData, POLL_INTERVAL); return () => clearInterval(i); }, [fetchData]);

  const handleStart = async () => {
    setIsStarting(true); setApiError(null);
    try {
      const r = await fetch(`${BACKEND}/api/tasks`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_type: "autonomous", priority: 9, intent_description: "Mulai siklus pemantauan lingkungan Bali secara otonom" }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      await fetchData();
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Gagal memulai siklus");
    } finally { setIsStarting(false); }
  };

  // ── Countdown ──
  const [countdown, setCountdown] = useState("");
  useEffect(() => {
    const iso = pendingTask?.execute_at;
    if (!iso) { setCountdown(""); return; }
    const tick = () => setCountdown(fmtCountdown(iso));
    tick(); const i = setInterval(tick, 1000); return () => clearInterval(i);
  }, [pendingTask?.execute_at]);

  // ── Scan tiles ──
  const scanTiles = useMemo(() => {
    if (!scanSummary) return [];
    const tiles: { label: string; value: string; sub: string; status: "good" | "warn" | "neutral" }[] = [];
    const w = scanSummary.weather;
    if (w?.avg_temp != null) tiles.push({ label: "Temp", value: `${Math.round(w.avg_temp)}°C`, sub: `max ${Math.round(w.max_temp)}°`, status: w.avg_temp > 33 ? "warn" : w.avg_temp > 30 ? "neutral" : "good" });
    const f = scanSummary.fire_hotspots;
    if (f?.count != null) tiles.push({ label: "Fire", value: `${f.count}`, sub: f.status === "WASPADA" ? "active" : "clear", status: f.count > 5 ? "warn" : f.count > 0 ? "neutral" : "good" });
    const e = scanSummary.earthquakes;
    if (e?.count_24h != null) tiles.push({ label: "Seismic", value: `${e.count_24h}`, sub: e.count_24h > 0 ? `max ${e.max_mag?.toFixed(1)}M` : "none", status: e.count_24h > 0 ? "neutral" : "good" });
    const a = scanSummary.air_quality;
    if (a?.worst_aqi != null) tiles.push({ label: "AQI", value: `${a.worst_aqi}`, sub: a.worst_location || "", status: a.worst_aqi > 3 ? "warn" : a.worst_aqi > 2 ? "neutral" : "good" });
    return tiles;
  }, [scanSummary]);

  // ── Expanded plan cases ──
  const [expandedCase, setExpandedCase] = useState<string | null>(null);

  // ── Render ──
  return (
    <div className="h-full flex flex-col min-h-0" style={{ fontFamily: "var(--font-geist-sans), system-ui, sans-serif", overflow: "hidden" }}>
      {/* Error */}
      <AnimatePresence>
        {apiError && (
          <motion.div
            className="text-[11px] px-3 py-1.5 mb-2 rounded flex-shrink-0"
            style={{ background: `${A.error}10`, color: A.error, border: `1px solid ${A.error}20`, fontFamily: "var(--font-geist-mono), monospace" }}
            initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
          >{apiError}</motion.div>
        )}
      </AnimatePresence>

      {/* Status bar */}
      <div className="flex-shrink-0 mb-2">
        <div className="flex items-center gap-3 flex-wrap" style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "11px" }}>
          <motion.span
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{ backgroundColor: stateColor(latestOtak?.state || "IDLE") }}
            animate={isLive ? { opacity: [0.4, 1, 0.4] } : {}}
            transition={{ duration: 1.6, repeat: isLive ? Infinity : 0, ease: "easeInOut" }}
          />
          <span className="font-medium" style={{ color: A.text }}>
            {runningTask ? `#${runningTask.id}` : "Agent Otak"}
          </span>
          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium"
            style={{ background: `${stateColor(latestOtak?.state || "IDLE")}15`, color: stateColor(latestOtak?.state || "IDLE") }}
          >{latestOtak?.state || "IDLE"}</span>
          {latestOtak?.metadata?.phase && (
            <span style={{ color: A.text3 }}>{latestOtak.metadata.phase as string}</span>
          )}
          <span className="ml-auto flex items-center gap-1" style={{ color: A.text3 }}>
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: sseConnected ? A.done : A.error }} />
            {sseConnected ? "live" : "off"}
          </span>
          <span style={{ color: A.text3 }}>{subAgentEvents.length} events</span>
          {(evaluation?.confidence ?? latestOtak?.metadata?.confidence) != null && (
            <span className="tabular-nums" style={{ color: A.text3 }}>
              conf {(evaluation?.confidence ?? latestOtak?.metadata?.confidence) as number}/10
            </span>
          )}
        </div>
      </div>

      {/* Hairline */}
      <div className="flex-shrink-0" style={{ height: "1px", background: A.border }} />

      {/* Content grid: LEFT (main) + RIGHT (sidebar) */}
      <div className="flex-1 flex min-h-0 pt-2.5" style={{ overflow: "hidden", gap: "24px" }}>
        {/* LEFT */}
        <div className="flex-1 flex flex-col min-h-0" style={{ gap: "10px", overflow: "hidden" }}>
          {isLive ? (
            <>
              {/* ── LIVE: Scan metrics ── */}
              {scanTiles.length > 0 && (
                <div className="flex-shrink-0">
                  <div className="flex items-baseline gap-2 mb-1.5" style={{ fontFamily: "var(--font-geist-mono), monospace" }}>
                    <span className="text-[10px] tracking-wider" style={{ color: A.text3 }}>01</span>
                    <span className="text-[10px] uppercase tracking-wider font-medium" style={{ color: A.text3 }}>Scan</span>
                  </div>
                  <div className="flex gap-2">
                    {scanTiles.map((t, i) => {
                      const col = t.status === "good" ? A.done : t.status === "warn" ? A.thinking : A.text3;
                      return (
                        <div key={i} className="flex-1 min-w-[72px] px-2 py-2 rounded text-center"
                          style={{ background: `${col}10`, border: `1px solid ${col}20` }}>
                          <div className="text-[9px] font-mono uppercase tracking-wider mb-0.5" style={{ color: A.text3 }}>{t.label}</div>
                          <div className="text-[16px] font-medium leading-tight tabular-nums" style={{ color: col, fontFamily: "var(--font-lora), Georgia, serif" }}>{t.value}</div>
                          <div className="text-[9px] font-mono mt-0.5 truncate" style={{ color: A.text3 }}>{t.sub}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* ── LIVE: Plan cases ── */}
              {planCases.length > 0 && (
                <div className="flex-shrink-0">
                  <div className="flex items-baseline gap-2 mb-1.5" style={{ fontFamily: "var(--font-geist-mono), monospace" }}>
                    <span className="text-[10px] tracking-wider" style={{ color: A.text3 }}>02</span>
                    <span className="text-[10px] uppercase tracking-wider font-medium" style={{ color: A.text3 }}>Plan</span>
                    <span className="text-[10px] ml-auto" style={{ color: A.text3 }}>{planCases.length} cases</span>
                  </div>
                  <div className="rounded overflow-hidden" style={{ border: `1px solid ${A.border}`, background: A.surface }}>
                    {planCases.map((c, i) => (
                      <div key={c.case_id} style={{ borderBottom: i < planCases.length - 1 ? `1px solid ${A.border}` : "none" }}>
                        <button
                          onClick={() => setExpandedCase(expandedCase === c.case_id ? null : c.case_id)}
                          className="w-full text-left px-3 py-1.5 flex items-center gap-2.5 group"
                          style={{ background: "transparent" }}
                        >
                          <span className="text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded flex-shrink-0 tabular-nums"
                            style={{ background: c.priority >= 8 ? `${A.error}18` : c.priority >= 5 ? `${A.thinking}18` : `${A.done}18`, color: c.priority >= 8 ? A.error : c.priority >= 5 ? A.thinking : A.done }}
                          >P{c.priority}</span>
                          <span className="text-[12px] flex-1 leading-snug" style={{ color: A.text }}>{c.title}</span>
                          <span className="text-[10px] font-mono" style={{ color: A.text3, transform: expandedCase === c.case_id ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>&#8594;</span>
                        </button>
                        <AnimatePresence>
                          {expandedCase === c.case_id && (
                            <motion.div className="px-3 pb-2 pl-10 space-y-1" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.2 }}>
                              <p className="text-[11px] leading-relaxed" style={{ color: A.text2 }}>{c.intent}</p>
                              <p className="text-[10px] font-mono leading-relaxed" style={{ color: A.text3 }}>{c.urgency_reason}</p>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ── LIVE: Reflection ── */}
              {evaluation && !evaluation.is_first_cycle && !evaluation.evaluation_failed && (
                <div className="flex-shrink-0 text-[11px] px-3 py-1.5 rounded" style={{ background: A.surface, color: A.text2 }}>
                  {evaluation.strategy_adjustments || ""}
                </div>
              )}

              {/* ── LIVE: Active runs (scrollable) ── */}
              {agentRuns.length > 0 && (
                <div className="flex-1 min-h-0 flex flex-col">
                  <div className="flex items-baseline gap-2 mb-1.5 flex-shrink-0" style={{ fontFamily: "var(--font-geist-mono), monospace" }}>
                    <span className="text-[10px] tracking-wider" style={{ color: A.text3 }}>03</span>
                    <span className="text-[10px] uppercase tracking-wider font-medium" style={{ color: A.text3 }}>Runs</span>
                    <span className="text-[10px] ml-auto" style={{ color: A.text3 }}>{agentRuns.length} active</span>
                  </div>
                  <div className="flex-1 overflow-y-auto min-h-0 space-y-1">
                    {agentRuns.map((r) => (
                      <motion.div key={r.caseId} className="px-3 py-1.5 rounded"
                        style={{ background: `${stateColor(r.state)}08`, border: `1px solid ${stateColor(r.state)}18` }}
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono font-semibold uppercase" style={{ color: stateColor(r.state) }}>{r.state}</span>
                          <span className="text-[12px] flex-1 truncate" style={{ color: A.text }}>{r.title}</span>
                          <span className="text-[9px] font-mono" style={{ color: A.text3 }}>P{r.priority}</span>
                        </div>
                        {r.narrative && <p className="text-[10px] mt-0.5 leading-relaxed truncate" style={{ color: A.text2 }}>{r.narrative}</p>}
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <>
              {/* ── IDLE: Last Cycle ── */}
              <div className="flex-shrink-0">
                <div className="flex items-baseline gap-2 mb-2" style={{ fontFamily: "var(--font-geist-mono), monospace" }}>
                  <span className="text-[10px] tracking-wider" style={{ color: A.text3 }}>01</span>
                  <span className="text-[10px] uppercase tracking-wider font-medium" style={{ color: A.text3 }}>Last Cycle</span>
                  {lastReport && <span className="text-[10px] ml-auto" style={{ color: A.text3 }}>{fmtDate(lastReport.created_at)}</span>}
                </div>
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
                  {lastReport ? (
                    <p className="text-[14px] leading-relaxed mb-2" style={{ color: A.text }}>
                      {lastReport.title || "Laporan"} <span style={{ color: A.text3 }}>&middot;</span> P:{lastReport.priority}
                      {lastReport.location ? <> <span style={{ color: A.text3 }}>&middot;</span> {lastReport.location}</> : null}
                    </p>
                  ) : (
                    <p className="text-[14px] mb-2" style={{ color: A.text3 }}>Belum ada siklus autonomous.</p>
                  )}
                  {countdown && (
                    <div className="flex items-center gap-2 mb-2" style={{ fontFamily: "var(--font-geist-mono), monospace" }}>
                      <span className="text-[10px] uppercase tracking-wider" style={{ color: A.text3 }}>Next wake</span>
                      <span className="text-[13px] tabular-nums" style={{ color: A.text2 }}>{countdown}</span>
                    </div>
                  )}
                  <button
                    onClick={handleStart} disabled={isStarting}
                    className="px-4 py-1.5 text-[12px] font-medium"
                    style={{
                      background: A.text, color: A.bg, borderRadius: "6px",
                      fontFamily: "var(--font-geist-sans), system-ui, sans-serif",
                      opacity: isStarting ? 0.5 : 1, cursor: isStarting ? "wait" : "pointer",
                    }}
                  >{isStarting ? "Starting..." : "Start Cycle"}</button>
                </motion.div>
              </div>

              {/* Hairline */}
              <div className="flex-shrink-0" style={{ height: "1px", background: A.border }} />

              {/* ── IDLE: History (scrollable) ── */}
              <div className="flex-1 min-h-0 flex flex-col">
                <div className="flex items-baseline gap-2 mb-1.5 flex-shrink-0" style={{ fontFamily: "var(--font-geist-mono), monospace" }}>
                  <span className="text-[10px] tracking-wider" style={{ color: A.text3 }}>02</span>
                  <span className="text-[10px] uppercase tracking-wider font-medium" style={{ color: A.text3 }}>History</span>
                  <span className="text-[10px] ml-auto" style={{ color: A.text3 }}>{history.length} reports</span>
                </div>
                {history.length > 0 ? (
                  <div className="flex-1 overflow-y-auto min-h-0 rounded" style={{ background: A.surface, border: `1px solid ${A.border}` }}>
                    {history.slice(0, 14).map((r, i) => (
                      <button
                        key={r.id}
                        onClick={() => router.push(`/laporan/${r.id}`)}
                        className="w-full text-left px-3 py-1.5 flex items-center gap-3 group"
                        style={{ background: "transparent", borderBottom: i < Math.min(history.length, 14) - 1 ? `1px solid ${A.border}` : "none" }}
                      >
                        <span className="text-[9px] font-mono w-5 flex-shrink-0" style={{ color: A.text3 }}>#{r.id}</span>
                        <span className="text-[12px] flex-1 truncate" style={{ color: A.text }}>{r.title || "Laporan"}</span>
                        <span className="text-[9px] font-mono flex-shrink-0" style={{ color: A.text3 }}>{fmtDate(r.created_at)}</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="text-[11px]" style={{ color: A.text3 }}>Belum ada laporan.</p>
                )}
              </div>
            </>
          )}
        </div>

        {/* RIGHT sidebar */}
        <div className="w-[260px] flex-shrink-0 flex flex-col min-h-0" style={{ gap: "10px" }}>
          {/* System status card */}
          <div className="flex-shrink-0 rounded p-3" style={{ background: A.surface, border: `1px solid ${A.border}` }}>
            <div className="flex items-baseline gap-2 mb-1.5" style={{ fontFamily: "var(--font-geist-mono), monospace" }}>
              <span className="text-[10px] uppercase tracking-wider font-medium" style={{ color: A.text3 }}>System</span>
              <span className="ml-auto flex items-center gap-1.5 text-[10px]" style={{ color: A.text3 }}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: sseConnected ? A.done : A.error }} />
                {sseConnected ? "connected" : "offline"}
              </span>
            </div>
            <div className="flex gap-4 text-[11px]" style={{ color: A.text2 }}>
              <span>{subAgentEvents.length} events</span>
              <span>{agentNames.length} participants</span>
            </div>
            {agentNames.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {agentNames.slice(0, 4).map(n => (
                  <span key={n} className="text-[9px] font-mono px-1.5 py-0.5 rounded" style={{ background: `${A.accent}15`, color: A.accent }}>{n}</span>
                ))}
              </div>
            )}
          </div>

          {/* Events feed (scrollable) */}
          {subAgentEvents.length > 0 && (
            <div className="flex-1 min-h-0 overflow-y-auto rounded" style={{ background: A.surface, border: `1px solid ${A.border}` }}>
              {subAgentEvents.slice(-20).reverse().map((e, i) => (
                <div key={i} className="px-2.5 py-1.5" style={{ borderBottom: i < Math.min(subAgentEvents.length, 20) - 1 ? `1px solid ${A.border}` : "none" }}>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1 h-1 rounded-full flex-shrink-0" style={{ backgroundColor: stateColor(e.state) }} />
                    <span className="text-[9px] font-mono uppercase" style={{ color: A.text3 }}>{e.state}</span>
                    <span className="text-[9px] font-mono ml-auto truncate max-w-[100px]" style={{ color: A.text3 }}>{e.node_id}</span>
                  </div>
                  {e.narrative && <p className="text-[10px] mt-0.5 leading-relaxed" style={{ color: A.text2, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{e.narrative}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
