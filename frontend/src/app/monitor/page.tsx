"use client";

import React, { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";
import {
  Flame, Leaf, Cloud, Globe,
  ArrowRight, Search, MapPin,
  Activity, CheckCircle2, AlertCircle,
  Cpu, Database, Clock,
} from "lucide-react";

interface Report {
  id: number;
  location: string;
  issue_type: string;
  created_at: string | null;
  severity: "High" | "Medium" | "Low";
  time: string;
}

interface StatusData {
  fastapi_active: boolean;
  modules_loaded: number;
  concurrent_tasks_active: number;
  total_reports: number;
  total_sessions: number;
  recent_reports: Report[];
}

const SEVERITY_COLOR: Record<string, { bg: string; text: string; dot: string }> = {
  High:   { bg: "#FEF2F2", text: "#B07068", dot: "#EF4444" },
  Medium: { bg: "#F1EFE8", text: "#5F5E5A", dot: "#888780" },
  Low:    { bg: "#F0FDF4", text: "#80A888", dot: "#10B981" },
};

function detectReportIcon(issue: string, location: string) {
  const s = `${issue} ${location}`.toLowerCase();
  if (/fire|hotspot|kebakaran|thermal/i.test(s)) return { icon: Flame, bg: "#F0ECE8", color: "#6B4A3A", label: "fire" };
  if (/vegetasi|geo|ndvi|satelit|deforestasi|hutan|mangrove|pohon/i.test(s)) return { icon: Leaf, bg: "#E8EDE8", color: "#4A5E4A", label: "vegetation" };
  if (/cuaca|weather|iklim|suhu|hujan|angin|kelembaban/i.test(s)) return { icon: Cloud, bg: "#E8ECF0", color: "#4A5670", label: "weather" };
  return { icon: Globe, bg: "#EEEDF0", color: "#5A4A6B", label: "osint" };
}

const AGENT_ROSTER = [
  { id: "geo_agent",      name: "geo_agent",      role: "Satellite & Spatial",  color: "#4A5E4A", bg: "#E8EDE8", icon: Leaf },
  { id: "water_agent",    name: "water_agent",    role: "Water Quality Sensor", color: "#4A5670", bg: "#E8ECF0", icon: Cloud },
  { id: "fire_agent",     name: "fire_agent",     role: "Thermal & Hotspot",    color: "#6B4A3A", bg: "#F0ECE8", icon: Flame },
  { id: "osint_agent",    name: "osint_agent",    role: "Media & Web Intel",    color: "#5A4A6B", bg: "#EEEDF0", icon: Globe },
];

const SUGGESTIONS = [
  "Audit vegetasi Kintamani",
  "Cek hotspot kebakaran Buleleng",
  "Analisis kualitas udara Denpasar",
  "Monitoring mangrove Tahura",
];

export default function MonitorPage() {
  const router = useRouter();
  const [data, setData] = useState<StatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [chatPrompt, setChatPrompt] = useState("");
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080";

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/api/status`);
      if (!res.ok) throw new Error("fetch failed");
      const json = await res.json();
      setData(json);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [backendUrl]);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 8000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleQuickChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatPrompt.trim()) return;
    router.push(`/dashboard?prompt=${encodeURIComponent(chatPrompt.trim())}`);
  };

  const container = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.06, delayChildren: 0.05 } },
  };
  const item = {
    hidden: { opacity: 0, y: 12 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.25, 0.1, 0.25, 1] as [number, number, number, number] } },
  };

  return (
    <>
      <NavBar />
      <main
        className="min-h-screen"
        style={{ backgroundColor: "var(--color-background-tertiary, #F0EFEA)" }}
      >
        <div className="max-w-7xl mx-auto px-6 lg:px-8 py-10">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1] as [number, number, number, number] }}
            className="mb-8"
          >
            <h1 className="text-[14px] font-medium text-[var(--pemali-text-primary)]">
              Monitor
            </h1>
            <p className="text-[12px] text-[var(--pemali-text-secondary)] mt-1">
              Real-time status sistem dan log audit lingkungan Bali
            </p>
          </motion.div>

          {/* Grid 2 kolom */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

            {/* ── KIRI: 3/5 ── */}
            <div className="lg:col-span-3 flex flex-col gap-5">

              {/* ═══ STATS ROW ═══ */}
              <motion.div variants={container} initial="hidden" animate="show" className="grid grid-cols-3 gap-4">
                {[
                  { label: "Total Reports", value: data?.total_reports ?? 0, icon: Database },
                  { label: "Active Sessions", value: data?.total_sessions ?? 0, icon: Activity },
                  { label: "Modules", value: data?.modules_loaded ?? 0, icon: Cpu },
                ].map((s) => (
                  <motion.div
                    key={s.label}
                    variants={item}
                    className="bg-white border-[0.5px] border-[var(--pemali-border)] rounded-xl p-5"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-[11px] text-[var(--pemali-text-muted)] uppercase tracking-[0.08em] font-medium">
                        {s.label}
                      </span>
                      <s.icon size={15} className="text-[#B4B2A9]" strokeWidth={1.5} />
                    </div>
                    <div className="text-[26px] font-medium text-[var(--pemali-text-primary)] tracking-tight">
                      {loading ? <span className="text-[var(--pemali-text-muted)]">...</span> : s.value}
                    </div>
                  </motion.div>
                ))}
              </motion.div>

              {/* ═══ INPUT AUDIT ═══ */}
              <motion.div
                variants={item} initial="hidden" animate="show"
                className="bg-white border-[0.5px] border-[var(--pemali-border)] rounded-xl p-5"
              >
                <div className="text-[11px] text-[var(--pemali-text-muted)] uppercase tracking-[0.08em] font-medium mb-4">
                  Inisiasi Audit
                </div>
                <form onSubmit={handleQuickChatSubmit}>
                  <div className="flex items-center gap-2 bg-[var(--pemali-bg)] border border-[var(--pemali-border)] rounded-xl px-4 py-[10px] focus-within:border-[var(--pemali-accent)]/50 transition-colors">
                    <Search size={15} className="text-[var(--pemali-text-muted)] shrink-0" strokeWidth={1.5} />
                    <input
                      type="text"
                      value={chatPrompt}
                      onChange={(e) => setChatPrompt(e.target.value)}
                      placeholder="Contoh: Audit degradasi vegetasi di Kintamani..."
                      className="w-full bg-transparent text-[13px] text-[var(--pemali-text-primary)] placeholder:italic placeholder:text-[var(--pemali-text-muted)] outline-none"
                    />
                    <button
                      type="submit"
                      disabled={!chatPrompt.trim()}
                      className="bg-[var(--pemali-text-primary)] text-white disabled:opacity-30 hover:opacity-90 px-5 py-2 rounded-lg text-[11px] font-medium transition-opacity shrink-0 flex items-center gap-1.5"
                    >
                      <span>Kirim</span>
                      <ArrowRight size={13} strokeWidth={2} />
                    </button>
                  </div>
                </form>
                <div className="flex flex-wrap gap-2 mt-3">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => setChatPrompt(s)}
                      className="text-[11px] text-[var(--pemali-text-secondary)] border border-[var(--pemali-border)] bg-white hover:bg-[var(--pemali-bg)] px-3 py-1.5 rounded-lg transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </motion.div>

              {/* ═══ LOG AUDIT ═══ */}
              <motion.div
                variants={item} initial="hidden" animate="show"
                className="bg-white border-[0.5px] border-[var(--pemali-border)] rounded-xl p-5"
              >
                <div className="flex items-center justify-between mb-5">
                  <div className="text-[11px] text-[var(--pemali-text-muted)] uppercase tracking-[0.08em] font-medium">
                    Log Pelanggaran Alam
                  </div>
                  <div className="flex items-center gap-1.5 text-[10px] text-[var(--pemali-text-muted)]">
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-60" style={{ backgroundColor: "#1D9E75" }} />
                      <span className="relative inline-flex rounded-full h-1.5 w-1.5" style={{ backgroundColor: "#1D9E75", opacity: 0.7 }} />
                    </span>
                    Live Feed
                  </div>
                </div>

                <div className="flex flex-col gap-3">
                  {loading ? (
                    <div className="text-[12px] text-[var(--pemali-text-muted)] py-10 text-center">
                      Memuat data...
                    </div>
                  ) : data?.recent_reports && data.recent_reports.length > 0 ? (
                    data.recent_reports.map((report, idx) => {
                      const sev = SEVERITY_COLOR[report.severity] || SEVERITY_COLOR.Low;
                      const meta = detectReportIcon(report.issue_type, report.location);
                      const Icon = meta.icon;
                      return (
                        <motion.div
                          key={report.id || idx}
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.3, delay: idx * 0.03 }}
                          className="flex items-start gap-3 p-4 border border-[var(--pemali-border)] rounded-xl hover:bg-[var(--pemali-bg)]/40 transition-colors"
                        >
                          {/* Icon semantic */}
                          <div
                            className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                            style={{ backgroundColor: meta.bg }}
                          >
                            <Icon size={16} style={{ color: meta.color }} strokeWidth={1.5} />
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2.5">
                              <span className="text-[13px] font-medium text-[var(--pemali-text-primary)] truncate">
                                {report.location}
                              </span>
                              <span className="text-[10px] font-mono text-[var(--pemali-text-muted)] shrink-0">
                                #{report.id}
                              </span>
                            </div>
                            <p className="text-[11px] text-[var(--pemali-text-secondary)] mt-0.5 truncate">
                              {report.issue_type}
                            </p>
                          </div>

                          {/* Severity + Time */}
                          <div className="flex flex-col items-end gap-1.5 shrink-0">
                            <div
                              className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[9px] font-medium uppercase tracking-wider"
                              style={{
                                backgroundColor: sev.bg,
                                color: sev.text,
                                border: report.severity === "Medium" ? "0.5px solid #D3D1C7" : "none",
                              }}
                            >
                              <span
                                className="w-1.5 h-1.5 rounded-full"
                                style={{ backgroundColor: sev.dot }}
                              />
                              {report.severity}
                            </div>
                            <span className="text-[10px] text-[var(--pemali-text-muted)] font-mono">
                              {report.time}
                            </span>
                          </div>
                        </motion.div>
                      );
                    })
                  ) : error ? (
                    <div className="text-[12px] text-[var(--state-error)] py-10 text-center border border-dashed border-[var(--pemali-border)] rounded-xl">
                      Gagal terhubung ke backend.
                    </div>
                  ) : (
                    <div className="text-[12px] text-[var(--pemali-text-muted)] py-10 text-center border border-dashed border-[var(--pemali-border)] rounded-xl">
                      Belum ada laporan audit.
                    </div>
                  )}
                </div>
              </motion.div>
            </div>

            {/* ── KANAN: 2/5 ── */}
            <div className="lg:col-span-2 flex flex-col gap-5">

              {/* ═══ SUB-AGENT ROSTER ═══ */}
              <motion.div
                variants={item} initial="hidden" animate="show"
                className="bg-white border-[0.5px] border-[var(--pemali-border)] rounded-xl p-5"
              >
                <div className="text-[11px] text-[var(--pemali-text-muted)] uppercase tracking-[0.08em] font-medium mb-4">
                  Sub-Agent Roster
                </div>
                <div className="flex flex-col gap-3">
                  {AGENT_ROSTER.map((agent, i) => (
                    <motion.div
                      key={agent.id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: 0.05 + i * 0.04 }}
                      className="flex items-center gap-3 p-3 border border-[var(--pemali-border)] rounded-xl"
                    >
                      <div
                        className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                        style={{ backgroundColor: agent.bg }}
                      >
                        <agent.icon size={16} style={{ color: agent.color }} strokeWidth={1.5} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-[12px] font-mono font-medium text-[var(--pemali-text-primary)]">
                          {agent.name}
                        </div>
                        <div className="text-[10px] text-[var(--pemali-text-secondary)] mt-0.5">
                          {agent.role}
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[#F5F4EF] border border-[var(--pemali-border)]">
                        <span className="w-1.5 h-1.5 rounded-full bg-[var(--pemali-text-muted)]" />
                        <span className="text-[9px] font-mono text-[var(--pemali-text-muted)] uppercase tracking-wider">
                          Standby
                        </span>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>

              {/* ═══ TRI HITA KARANA ═══ */}
              <motion.div
                variants={item} initial="hidden" animate="show"
                className="bg-white border-[0.5px] border-[var(--pemali-border)] rounded-xl p-5"
              >
                <div className="text-[11px] tracking-[0.1em] uppercase font-medium mb-5" style={{ color: "#888780" }}>
                  Tri Hita Karana
                </div>
                <div className="flex flex-col gap-5">
                  {[
                    {
                      num: "01",
                      title: "Parahyangan",
                      desc: "Keseimbangan spiritual. Audit kognitif AI didesain menghormati nilai kearifan desa adat dan kesucian alam Bali.",
                    },
                    {
                      num: "02",
                      title: "Pawongan",
                      desc: "Kolaborasi sosial. Keterbukaan data anomali dan log otonom yang dapat diakses oleh masyarakat desa adat.",
                    },
                    {
                      num: "03",
                      title: "Palemahan",
                      desc: "Harmoni lingkungan. Pemantauan sensor ekologis asinkron dalam menanggulangi ancaman kerusakan fisik alam.",
                    },
                  ].map((thk) => (
                    <div
                      key={thk.num}
                      className="pl-3"
                      style={{
                        borderLeft: "2px solid #5B8DEF",
                      }}
                    >
                      <div className="text-[10px] font-mono tracking-wider mb-1" style={{ color: "#B4B2A9" }}>
                        {thk.num}
                      </div>
                      <div className="text-[13px] font-medium text-[var(--pemali-text-primary)] mb-1">
                        {thk.title}
                      </div>
                      <p className="text-[11px] text-[var(--pemali-text-secondary)] leading-relaxed">
                        {thk.desc}
                      </p>
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* ═══ HEARTBEAT ═══ */}
              <motion.div
                variants={item} initial="hidden" animate="show"
                className="bg-white border-[0.5px] border-[var(--pemali-border)] rounded-xl p-5"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-[11px] text-[var(--pemali-text-muted)] uppercase tracking-[0.08em] font-medium mb-1">
                      System
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="relative flex h-2 w-2">
                        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${error ? "bg-red-400" : "bg-green-400"}`} />
                        <span className={`relative inline-flex rounded-full h-2 w-2 ${error ? "bg-red-500" : "bg-green-500"}`} />
                      </span>
                      <span className="text-[13px] font-medium text-[var(--pemali-text-primary)]">
                        {error ? "Disconnected" : "Operational"}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px] text-[var(--pemali-text-muted)] font-mono">
                    <Clock size={13} strokeWidth={1.5} />
                    <span>8s poll</span>
                  </div>
                </div>
                <div className="mt-3 text-[11px] text-[var(--pemali-text-secondary)]">
                  {data?.fastapi_active
                    ? `FastAPI aktif · ${data.modules_loaded} module terdaftar`
                    : "Menunggu koneksi backend..."}
                </div>
              </motion.div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
