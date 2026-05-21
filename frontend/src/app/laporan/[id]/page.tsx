"use client";

/* Direction: Anthropic Terminal — Warm Editorial Report Detail */

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import AiBubble from "@/components/pemali/AiBubble";
import { cn } from "@/lib/utils";

interface RawSensorEntry {
  id: number;
  agent_name: string;
  tool_name: string;
  raw_payload: Record<string, unknown>;
  created_at: string;
}

interface ReportDetail {
  id: number;
  session_id: string;
  source: "autonomous" | "user";
  title: string;
  location: string;
  issue_type: string;
  priority: number;
  narrative_report: string;
  thk_alignment: Record<string, string> | null;
  metadata: Record<string, unknown> | null;
  raw_sensor_data: RawSensorEntry[];
  created_at: string;
}

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8080";

const priorityColor = (p: number) => {
  if (p >= 8) return "rgb(176,112,104)";
  if (p >= 6) return "rgb(212,149,106)";
  return "rgb(128,168,136)";
};

const priorityLabel = (p: number) => {
  if (p >= 8) return "Kritis";
  if (p >= 6) return "Prioritas";
  return "Rutin";
};

const parseUtc = (iso: string) => {
  if (!iso.endsWith("Z") && !iso.includes("+")) return new Date(iso + "Z");
  return new Date(iso);
};

const formatDate = (iso: string) => {
  if (!iso) return "-";
  return parseUtc(iso).toLocaleString("id-ID", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Makassar",
    timeZoneName: "short",
  });
};

const staggerItem = {
  hidden: { opacity: 0, y: 12 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: [0.0, 0.0, 0.2, 1] as const },
  },
};

export default function LaporanDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params.id) return;
    const id = Number(params.id);
    if (isNaN(id)) {
      setError("ID laporan tidak valid");
      setLoading(false);
      return;
    }

    setLoading(true);
    fetch(`${BACKEND}/api/laporan/${id}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: ReportDetail) => {
        setReport(data);
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
      });
  }, [params.id]);

  // Loading
  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--pemali-bg)] flex items-center justify-center">
        <div className="flex items-center gap-3 text-[var(--pemali-text-muted)]">
          <span className="inline-block w-2 h-2 rounded-full bg-[var(--pemali-accent)] animate-pulse" />
          <span className="text-[14px]">Memuat laporan...</span>
        </div>
      </div>
    );
  }

  // Error
  if (error || !report) {
    return (
      <div className="min-h-screen bg-[var(--pemali-bg)] flex items-center justify-center">
        <div className="text-center">
          <p className="text-[var(--state-error)] text-[15px] mb-3">{error || "Laporan tidak ditemukan"}</p>
          <button
            onClick={() => {
              if (typeof window !== "undefined" && document.referrer.includes("/agentic")) {
                router.push("/agentic");
              } else {
                router.push("/laporan");
              }
            }}
            className="text-[13px] text-[var(--pemali-accent)] hover:underline font-mono"
          >
            ← Kembali
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--pemali-bg)] text-[var(--pemali-text-primary)]">
      <div className="max-w-3xl mx-auto px-5 pt-12 pb-24">
        {/* Back navigation */}
        <motion.button
          onClick={() => {
            if (typeof window !== "undefined" && document.referrer.includes("/agentic")) {
              router.push("/agentic");
            } else {
              router.push("/laporan");
            }
          }}
          className="text-[12px] text-[var(--pemali-text-muted)] hover:text-[var(--pemali-text-primary)] transition-colors mb-6 inline-flex items-center gap-1 font-mono"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <span>←</span>
          <span>{typeof window !== "undefined" && document.referrer.includes("/agentic") ? "Kembali ke Agentic" : "Semua laporan"}</span>
        </motion.button>

        {/* Hero */}
        <motion.div
          className="mb-10"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.0, 0.0, 0.2, 1] }}
        >
          <div className="flex items-center gap-3 mb-3 flex-wrap">
            <span
              className="text-[11px] px-2.5 py-1 rounded-full font-[500] uppercase tracking-wider"
              style={{
                backgroundColor: `${priorityColor(report.priority)}16`,
                color: priorityColor(report.priority),
              }}
            >
              {priorityLabel(report.priority)} P{report.priority}
            </span>
            <span className="text-[11px] text-[var(--pemali-text-muted)] font-mono">
              {report.source === "autonomous" ? "◇ Otonom" : "○ Manual"}
            </span>
            {report.location && (
              <span className="text-[11px] text-[var(--pemali-text-muted)] font-mono">
                {report.location}
              </span>
            )}
          </div>

          <h1 className="text-[30px] font-[500] tracking-[-0.02em] leading-tight mb-2">
            {report.title || report.issue_type || "Laporan Audit"}
          </h1>
          <p className="text-[13px] text-[var(--pemali-text-muted)] font-mono">
            {formatDate(report.created_at)}
          </p>
        </motion.div>

        {/* Divider */}
        <hr className="border-[var(--pemali-border)] mb-10" />

        {/* Narrative Report */}
        <motion.div className="mb-12" variants={staggerItem} initial="hidden" animate="show">
          <h2 className="text-[12px] uppercase tracking-wider text-[var(--pemali-text-muted)] font-[500] mb-4 font-mono">
            Narasi Laporan
          </h2>
          <div
            className="prose prose-base max-w-none"
            style={{
              fontFamily: "var(--font-geist-sans), ui-sans-serif",
              color: "var(--pemali-text-primary)",
              lineHeight: 1.8,
              fontSize: "15px",
            }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {report.narrative_report || "_Belum ada narasi laporan._"}
            </ReactMarkdown>
          </div>
        </motion.div>

        {/* THK Alignment */}
        {report.thk_alignment && Object.keys(report.thk_alignment).length > 0 && (
          <motion.div className="mb-12" variants={staggerItem} initial="hidden" animate="show">
            <h2 className="text-[12px] uppercase tracking-wider text-[var(--pemali-text-muted)] font-[500] mb-4 font-mono">
              Tri Hita Karana
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { key: "parahyangan", label: "Parahyangan", desc: "Hubungan spiritual" },
                { key: "pawongan", label: "Pawongan", desc: "Hubungan sosial" },
                { key: "palemahan", label: "Palemahan", desc: "Hubungan alam" },
              ].map(({ key, label, desc }) => (
                <div
                  key={key}
                  className="px-4 py-3 rounded-lg bg-[var(--pemali-surface)] border border-[var(--pemali-border)]"
                >
                  <div className="text-[12px] uppercase tracking-wider text-[var(--pemali-text-muted)] font-[500] mb-1 font-mono">
                    {label}
                  </div>
                  <div className="text-[11px] text-[var(--pemali-text-muted)]">{desc}</div>
                  <p className="text-[13px] text-[var(--pemali-text-secondary)] mt-1.5 leading-relaxed">
                    {report.thk_alignment?.[key] || "-"}
                  </p>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Sub-Agent Outputs */}
        {report.raw_sensor_data && report.raw_sensor_data.length > 0 && (
          <motion.div className="mb-12" variants={staggerItem} initial="hidden" animate="show">
            <h2 className="text-[12px] uppercase tracking-wider text-[var(--pemali-text-muted)] font-[500] mb-4 font-mono">
              Data Sensor Mentah
            </h2>
            <div className="space-y-2">
              {report.raw_sensor_data.map((entry) => (
                <div
                  key={entry.id}
                  className="px-4 py-3 rounded-lg bg-[var(--pemali-surface)] border border-[var(--pemali-border)]"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[12px] font-[500] text-[var(--pemali-accent)] font-mono">
                      {entry.agent_name || entry.tool_name}
                    </span>
                    <span className="text-[11px] text-[var(--pemali-text-muted)] font-mono">
                      {entry.tool_name}
                    </span>
                  </div>
                  <pre className="text-[12px] text-[var(--pemali-text-secondary)] overflow-x-auto font-mono leading-relaxed whitespace-pre-wrap">
                    {JSON.stringify(entry.raw_payload, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Metadata */}
        {report.metadata && Object.keys(report.metadata).length > 0 && (
          <motion.div className="mb-12" variants={staggerItem} initial="hidden" animate="show">
            <h2 className="text-[12px] uppercase tracking-wider text-[var(--pemali-text-muted)] font-[500] mb-4 font-mono">
              Metadata
            </h2>
            <pre className="text-[12px] text-[var(--pemali-text-muted)] font-mono leading-relaxed whitespace-pre-wrap bg-[var(--pemali-surface)] rounded-lg px-4 py-3 border border-[var(--pemali-border)] overflow-x-auto">
              {JSON.stringify(report.metadata, null, 2)}
            </pre>
          </motion.div>
        )}
      </div>

      {/* AiBubble — scoped RAG floating chat */}
      <AiBubble laporanId={report.id} />
    </div>
  );
}
