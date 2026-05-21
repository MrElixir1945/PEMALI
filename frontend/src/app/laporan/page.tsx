"use client";

/* Direction: Anthropic Terminal — Warm Editorial Report List */

import React, { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import ReportCard from "@/components/pemali/ReportCard";
import NavBar from "@/components/NavBar";
import { cn } from "@/lib/utils";

interface ReportSummary {
  id: number;
  session_id: string;
  source: "autonomous" | "user";
  title: string;
  location: string;
  issue_type: string;
  priority: number;
  narrative_preview: string;
  created_at: string;
}

interface ReportListResponse {
  total: number;
  reports: ReportSummary[];
}

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "";

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.1 },
  },
};

export default function LaporanPage() {
  const router = useRouter();
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterSource, setFilterSource] = useState<string>("all");
  const [filterLocation, setFilterLocation] = useState("");

  const fetchReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filterSource !== "all") params.set("source", filterSource);
      if (filterLocation.trim()) params.set("location", filterLocation.trim());
      params.set("limit", "50");

      const res = await fetch(`${BACKEND}/api/laporan?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: ReportListResponse = await res.json();
      setReports(data.reports);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal memuat laporan");
    } finally {
      setLoading(false);
    }
  }, [filterSource, filterLocation]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  return (
    <div className="min-h-screen bg-[var(--pemali-bg)] text-[var(--pemali-text-primary)]">
      <NavBar />
      <div className="max-w-3xl mx-auto px-5 py-12">
        {/* Header */}
        <motion.div
          className="mb-10"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.0, 0.0, 0.2, 1] }}
        >
          <h1 className="text-[28px] font-[500] tracking-[-0.02em] mb-2">
            Laporan Audit
          </h1>
          <p className="text-[14px] text-[var(--pemali-text-secondary)]">
            Arsip semua laporan audit — otonom dan manual.
          </p>
        </motion.div>

        {/* Filters */}
        <motion.div
          className="flex items-center gap-3 mb-8 flex-wrap"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <select
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value)}
            className={cn(
              "text-[13px] px-3 py-2 rounded-md",
              "bg-[var(--pemali-surface)] border border-[var(--pemali-border)]",
              "text-[var(--pemali-text-primary)] outline-none",
              "focus:border-[var(--pemali-accent)] transition-colors"
            )}
          >
            <option value="all">Semua Sumber</option>
            <option value="autonomous">Otonom</option>
            <option value="user">Manual</option>
          </select>

          <input
            type="text"
            value={filterLocation}
            onChange={(e) => setFilterLocation(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchReports()}
            placeholder="Filter lokasi..."
            className={cn(
              "text-[13px] px-3 py-2 rounded-md w-48",
              "bg-[var(--pemali-surface)] border border-[var(--pemali-border)]",
              "text-[var(--pemali-text-primary)] placeholder:text-[var(--pemali-text-muted)]",
              "outline-none focus:border-[var(--pemali-accent)] transition-colors"
            )}
          />

          <span className="text-[12px] text-[var(--pemali-text-muted)] font-mono">
            {reports.length} laporan
          </span>
        </motion.div>

        {/* Error state */}
        {error && (
          <div className="text-[14px] text-[var(--state-error)] bg-[rgba(176,112,104,0.06)] px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-24 bg-[var(--pemali-surface)] rounded-lg animate-pulse"
              />
            ))}
          </div>
        )}

        {/* Empty */}
        {!loading && !error && reports.length === 0 && (
          <motion.div
            className="text-center py-16"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <p className="text-[14px] text-[var(--pemali-text-muted)]">
              Belum ada laporan audit.
            </p>
            <p className="text-[13px] text-[var(--pemali-text-muted)] mt-1">
              Mulai audit dari dashboard untuk membuat laporan pertama.
            </p>
          </motion.div>
        )}

        {/* Report list */}
        <motion.div
          className="space-y-3"
          variants={container}
          initial="hidden"
          animate="show"
        >
          {reports.map((r, i) => (
            <div key={r.id} style={{ animationDelay: `${i * 0.05}s` }}>
              <ReportCard
                id={r.id}
                title={r.title}
                source={r.source}
                priority={r.priority}
                location={r.location}
                issue_type={r.issue_type}
                narrative_preview={r.narrative_preview}
                created_at={r.created_at}
              />
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
