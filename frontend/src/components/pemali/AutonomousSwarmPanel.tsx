"use client";

/* Direction: Refined Anthropic Editorial — Swarm Panel */

import React, { useEffect, useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { useTelemetryStore } from "@/stores/telemetryStore";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// ─── Anthropic palette ───
const A = {
  bg: "#FFFFFF",
  surface: "#F1EFE8",
  surfaceHover: "#E8E6DC",
  text: "#1A1916",
  text2: "#5F5E5A",
  text3: "#888780",
  accent: "#8B5CF6",
  border: "rgba(26,25,22,0.08)",
  thinking: "#8B5CF6",
  executing: "#10B981",
  done: "#10B981",
  error: "#EF4444",
};

// ─── Types ───
interface LaporanSummary {
  id: number; title: string; priority: number; location: string;
  metadata: Record<string, unknown> | null; created_at: string;
}
interface ReportDetail {
  id: number; session_id: string; source: "autonomous" | "user"; title: string; location: string;
  issue_type: string; priority: number; narrative_report: string; thk_alignment: Record<string, string> | null;
  metadata: Record<string, unknown> | null; created_at: string;
}
interface TaskResponse { total: number; tasks: Array<{ id: number; task_type: string; priority: number; intent_description: string; execute_at: string; status: string; retries: number; last_error: string | null; created_at: string; }>; }
interface LaporanListResponse { total: number; reports: LaporanSummary[]; }
interface AgentRunState { caseId: string; title: string; priority: number; state: string; narrative: string; urgencyReason: string; }
interface CaseItem { case_id: string; title: string; priority: number; intent: string; urgency_reason: string; }
interface EvaluationData { was_decision_correct?: boolean; strategy_adjustments?: string; confidence?: number; is_first_cycle?: boolean; evaluation_failed?: boolean; }
interface ScanSummary { weather?: { avg_temp: number; max_temp: number }; fire_hotspots?: { count: number; status: string }; earthquakes?: { count_24h: number; max_mag: number }; air_quality?: { worst_aqi: number; worst_location: string }; }

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8080";
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
  const [lastReportDetail, setLastReportDetail] = useState<ReportDetail | null>(null);
  const [showReportDetail, setShowReportDetail] = useState(false);
  const [justTriggered, setJustTriggered] = useState(false);
  const [activeTab, setActiveTab] = useState<"live" | "history">("live");
  const [history, setHistory] = useState<LaporanSummary[]>([]);
  const [pendingTask, setPendingTask] = useState<{ id: number; execute_at: string } | null>(null);
  const [runningTask, setRunningTask] = useState<{ id: number } | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // ── Derived ──
  const otakEvents = useMemo(() => events.filter((e) => e.node_id === "agent_otak"), [events]);
  const latestOtak = otakEvents[otakEvents.length - 1];
  const isLive = useMemo(() => {
    if (isStarting) return true;
    if (justTriggered) return true;
    if (latestOtak && latestOtak.state !== "DONE" && latestOtak.state !== "ERROR") return true;
    if (runningTask) return true;
    return false;
  }, [latestOtak, runningTask, justTriggered, isStarting]);

  const showLiveContent = useMemo(() => isLive && activeTab === "live", [isLive, activeTab]);

  // Reset tab to live when isLive becomes false
  useEffect(() => {
    if (!isLive) {
      setActiveTab("live");
    }
  }, [isLive]);

  // Clear justTriggered as soon as we receive live events
  useEffect(() => {
    if (latestOtak) {
      setJustTriggered(false);
    }
  }, [latestOtak]);

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
      if (lr.ok) {
        const d: LaporanListResponse = await lr.json();
        setLastReport(d.reports[0] || null);
        if (d.reports[0]) {
          const detailRes = await fetch(`${BACKEND}/api/laporan/${d.reports[0].id}`);
          if (detailRes.ok) {
            const detailData = await detailRes.json();
            setLastReportDetail(detailData);
          }
        }
      }
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
      setJustTriggered(true);
      setTimeout(() => setJustTriggered(false), 20000); // auto-expire after 20s
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
      <div className="flex-shrink-0 mb-3 px-1">
        <div className="flex items-center gap-3 flex-wrap font-mono text-[10px]" style={{ color: A.text3 }}>
          <motion.span
            className="w-1.5 h-1.5 rounded-full flex-shrink-0"
            style={{ backgroundColor: stateColor(isLive ? (latestOtak?.state || "THINKING") : "IDLE") }}
            animate={isLive ? { opacity: [0.4, 1, 0.4] } : {}}
            transition={{ duration: 1.6, repeat: isLive ? Infinity : 0, ease: "easeInOut" }}
          />
          <span className="font-semibold uppercase tracking-wider text-[11px]" style={{ color: A.text }}>
            {isLive ? `Siklus Aktif #${runningTask?.id || pendingTask?.id || ""}` : "Siklus Otonom"}
          </span>
          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider"
            style={{ background: `${stateColor(isLive ? (latestOtak?.state || "THINKING") : "IDLE")}15`, color: stateColor(isLive ? (latestOtak?.state || "THINKING") : "IDLE") }}
          >
            {isLive ? (latestOtak?.state || "INITIALIZING") : "Ready / Siap"}
          </span>
          {latestOtak?.metadata?.phase && (
            <span className="uppercase" style={{ color: A.text2 }}>Phase: {latestOtak.metadata.phase as string}</span>
          )}
          <span className="ml-auto flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: sseConnected ? A.done : A.error }} />
            <span>REAL-TIME TELEMETRY</span>
          </span>
        </div>
      </div>

      {isLive && (
        <div className="flex justify-end gap-1.5 mb-3 px-1 flex-shrink-0">
          <button
            onClick={() => setActiveTab("live")}
            className="px-2.5 py-1 text-[9px] uppercase font-mono tracking-wider font-semibold rounded transition-all duration-200"
            style={{
              background: activeTab === "live" ? A.text : "transparent",
              color: activeTab === "live" ? A.bg : A.text2,
              border: `1.5px solid ${activeTab === "live" ? A.text : "rgba(26,25,22,0.12)"}`
            }}
          >
            ● Live Monitor
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className="px-2.5 py-1 text-[9px] uppercase font-mono tracking-wider font-semibold rounded transition-all duration-200"
            style={{
              background: activeTab === "history" ? A.text : "transparent",
              color: activeTab === "history" ? A.bg : A.text2,
              border: `1.5px solid ${activeTab === "history" ? A.text : "rgba(26,25,22,0.12)"}`
            }}
          >
            Laporan & Histori
          </button>
        </div>
      )}

      {/* Hairline */}
      <div className="flex-shrink-0" style={{ height: "1px", background: A.border }} />

      {/* Content grid: LEFT (main) + RIGHT (sidebar) */}
      <div className="flex-1 flex min-h-0 pt-2.5" style={{ overflow: "hidden", gap: "24px" }}>
        {/* LEFT */}
        <div className="flex-1 flex flex-col min-h-0" style={{ gap: "10px", overflow: "hidden" }}>
          {showLiveContent ? (
            <>
              {/* ── Swarm Live Audit Track ── */}
              <div className="flex-shrink-0 rounded p-4 mb-3 border relative overflow-hidden" style={{ background: A.surface, borderColor: A.border }}>
                <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[#8B5CF6]/40 to-transparent animate-[pulse_2s_infinite]" />
                
                <div className="flex items-center gap-3 mb-3">
                  <div className="relative w-3.5 h-3.5 flex items-center justify-center">
                    <span className="absolute inline-flex h-full w-full rounded-full bg-[#8B5CF6]/30 animate-ping" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-[#8B5CF6]" />
                  </div>
                  <div>
                    <h4 className="text-[12px] font-semibold" style={{ color: A.text }}>Pemali Swarm: Active Environmental Audit</h4>
                    <p className="text-[9px]" style={{ color: A.text3 }}>Multi-agent execution & logical inference routing</p>
                  </div>
                  <span className="ml-auto text-[9px] font-mono bg-black/[0.04] px-1.5 py-0.5 rounded uppercase" style={{ color: A.text2 }}>
                    {latestOtak?.state || "RUNNING"}
                  </span>
                </div>

                <div className="space-y-1.5 mt-2 font-mono text-[10px]">
                  {[
                    { label: "Inisialisasi Swarm & Database Connection Pool", check: true },
                    { label: "Manager Agent: Menganalisis kondisi anomali satelit & cuaca", check: latestOtak?.state !== "SPAWNING" },
                    { label: "Membagi kasus prioritas dan menyusun Directed Acyclic Graph (DAG)", check: planCases.length > 0 },
                    { label: "Spawning sub-agents spesialisasi (OSINT, Geo, Fire, Seismic)", check: agentRuns.length > 0 },
                    { label: "Menyelesaikan laporan audit & sinkronisasi RAG memory", check: latestOtak?.state === "DONE" }
                  ].map((step, idx) => {
                    const active = idx === 0 ? true : 
                                   idx === 1 ? latestOtak?.state === "THINKING" || planCases.length > 0 :
                                   idx === 2 ? planCases.length > 0 :
                                   idx === 3 ? agentRuns.length > 0 :
                                   latestOtak?.state === "DONE";
                    const done = step.check;
                    return (
                      <div key={idx} className="flex items-center gap-2 py-0.5 transition-opacity duration-300" style={{ opacity: active || done ? 1 : 0.35 }}>
                        <span className="flex-shrink-0 w-3.5 h-3.5 rounded-full flex items-center justify-center text-[8px] font-bold"
                          style={{
                            background: done ? `${A.done}18` : active ? `${A.thinking}18` : "rgba(26,25,22,0.04)",
                            color: done ? A.done : active ? A.thinking : A.text3,
                            border: `1px solid ${done ? `${A.done}30` : active ? `${A.thinking}30` : "transparent"}`
                          }}
                        >
                          {done ? "✓" : active ? "●" : idx + 1}
                        </span>
                        <span className="flex-1 truncate" style={{ color: done ? A.text : active ? A.text : A.text3 }}>{step.label}</span>
                        {active && !done && (
                          <span className="text-[9px] animate-pulse" style={{ color: A.thinking }}>running...</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

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
                    <>
                      <p className="text-[14px] leading-relaxed mb-2" style={{ color: A.text }}>
                        {lastReport.title || "Laporan"} <span style={{ color: A.text3 }}>&middot;</span> <span className="text-[11px] font-mono px-1.5 py-0.5 rounded" style={{ background: lastReport.priority >= 8 ? `${A.error}15` : `${A.accent}15`, color: lastReport.priority >= 8 ? A.error : A.accent }}>{lastReport.priority >= 8 ? "Prioritas Kritis" : lastReport.priority >= 5 ? "Prioritas Tinggi" : "Rutin"}</span>
                        {lastReport.location ? <> <span style={{ color: A.text3 }}>&middot;</span> {lastReport.location}</> : null}
                      </p>

                      {lastReportDetail && (
                        <div className="mt-2 flex flex-col gap-1.5 mb-3">
                          <button
                            onClick={() => setShowReportDetail(!showReportDetail)}
                            className="text-[10px] uppercase font-mono tracking-wider font-semibold text-[#8B5CF6] hover:underline text-left inline-flex items-center gap-1.5"
                          >
                            <span>{showReportDetail ? "↓ Sembunyikan Laporan" : "→ Lihat Hasil Laporan Otonom"}</span>
                          </button>
                          
                          <AnimatePresence>
                            {showReportDetail && (
                              <motion.div
                                initial={{ opacity: 0, y: -8 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -8 }}
                                transition={{ duration: 0.2, ease: "easeOut" }}
                                className="mt-1.5"
                              >
                                <div className="p-4 rounded-xl border max-h-[300px] overflow-y-auto leading-relaxed text-[12px] font-sans prose prose-neutral max-w-none"
                                  style={{
                                    background: "#FCFAF6",
                                    borderColor: "rgba(26,25,22,0.06)",
                                    color: "#1A1916",
                                    boxShadow: "inset 0 2px 8px rgba(0,0,0,0.015)"
                                  }}
                                >
                                  <div className="flex items-center justify-between pb-2 mb-3 border-b border-[rgba(26,25,22,0.06)] font-mono text-[9px] uppercase tracking-wider text-[#888780]">
                                    <span>Hasil Sintesis Swarm</span>
                                    <span>{fmtDate(lastReportDetail.created_at)}</span>
                                  </div>
                                  <h3 className="font-serif text-[18px] font-semibold mb-2 text-[#1A1916]">
                                    {lastReportDetail.title}
                                  </h3>
                                  <div className="space-y-3 prose-p:leading-relaxed prose-headings:font-serif">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                      {lastReportDetail.narrative_report}
                                    </ReactMarkdown>
                                  </div>
                                  
                                  {lastReportDetail.thk_alignment && (
                                    <div className="mt-4 pt-3 border-t border-[rgba(26,25,22,0.06)]">
                                      <div className="font-mono text-[9px] uppercase tracking-wider text-[#888780] mb-2 font-semibold">
                                        Penyelarasan Tri Hita Karana (THK):
                                      </div>
                                      <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 font-mono text-[10px]">
                                        {Object.entries(lastReportDetail.thk_alignment).map(([k, v]) => (
                                          <div key={k} className="p-2 rounded bg-black/[0.02] border border-black/[0.03]">
                                            <span className="font-semibold uppercase block mb-0.5 text-[#8B5CF6] text-[8px] tracking-wider">{k}</span>
                                            <span className="text-[10px] text-[#5F5E5A] leading-snug">{v}</span>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </div>
                      )}
                    </>
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
                  >{isStarting ? "Memulai..." : "Mulai Audit Agent"}</button>
                </motion.div>
              </div>

              {/* Hairline */}
              <div className="flex-shrink-0" style={{ height: "1px", background: A.border }} />

              {/* ── IDLE: History (scrollable) ── */}
              <div className="flex-1 min-h-0 flex flex-col">
                <div className="flex items-center gap-2 mb-1.5 flex-shrink-0" style={{ fontFamily: "var(--font-geist-mono), monospace" }}>
                  <span className="text-[10px] tracking-wider" style={{ color: A.text3 }}>02</span>
                  <span className="text-[10px] uppercase tracking-wider font-medium" style={{ color: A.text3 }}>History</span>
                  <button
                    onClick={() => router.push("/laporan")}
                    className="text-[10px] ml-auto hover:underline font-mono uppercase tracking-wider text-[#8B5CF6] font-semibold"
                  >
                    Lihat Semua Laporan →
                  </button>
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
                        <span className="text-[9px] font-mono w-5 flex-shrink-0" style={{ color: A.text3 }}>{String(history.length - i).padStart(2, "0")}</span>
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
        <div className="w-[260px] flex-shrink-0 flex flex-col min-h-0">
          <div className="flex-1 min-h-0 flex flex-col rounded" style={{ background: A.surface, border: `1px solid ${A.border}`, overflow: "hidden" }}>
            <div className="flex-shrink-0 px-3 py-2 border-b" style={{ borderColor: A.border, background: A.surface }}>
              <div className="flex items-center gap-1.5 font-mono text-[9px]" style={{ color: A.text3 }}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: sseConnected ? A.done : A.error }} />
                <span>TELEMETRY STREAM</span>
                <span className="ml-auto uppercase tracking-wider">{sseConnected ? "Active" : "Offline"}</span>
              </div>
            </div>
            {subAgentEvents.length > 0 ? (
              <div className="flex-1 overflow-y-auto min-h-0 divide-y divide-[rgba(26,25,22,0.06)]">
                {subAgentEvents.slice(-30).reverse().map((e, i) => (
                  <div key={i} className="px-3 py-2 hover:bg-black/[0.01] transition-colors">
                    <div className="flex items-center gap-1.5">
                      <span className="w-1 h-1 rounded-full flex-shrink-0" style={{ backgroundColor: stateColor(e.state) }} />
                      <span className="text-[9px] font-mono uppercase font-semibold" style={{ color: stateColor(e.state) }}>{e.state}</span>
                      <span className="text-[9px] font-mono ml-auto" style={{ color: A.text3 }}>{e.node_id}</span>
                    </div>
                    {e.narrative && <p className="text-[10px] mt-1 leading-relaxed" style={{ color: A.text2 }}>{e.narrative}</p>}
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
                <span className="text-[20px] mb-2">👁️‍🗨️</span>
                <p className="text-[11px] leading-relaxed max-w-[180px]" style={{ color: A.text3 }}>
                  Belum ada aktivitas otonom terdeteksi. Mulai audit untuk melihat telemetry stream.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
