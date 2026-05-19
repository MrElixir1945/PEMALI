"use client";

/* Direction: Anthropic Terminal — Warm Editorial Report Card */

import React from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

interface ReportCardProps {
  id: number;
  title: string;
  source: "autonomous" | "user";
  priority: number;
  location: string;
  issue_type: string;
  narrative_preview: string;
  created_at: string;
}

const priorityColor = (p: number) => {
  if (p >= 8) return "rgb(176,112,104)"; // error-red (kritis)
  if (p >= 6) return "rgb(212,149,106)"; // accent-orange
  return "rgb(128,168,136)";              // complete-green (normal)
};

const priorityLabel = (p: number) => {
  if (p >= 8) return "Kritis";
  if (p >= 6) return "Prioritas";
  return "Rutin";
};

const sourceLabel = (s: string) => (s === "autonomous" ? "Otonom" : "Manual");
const sourceIcon = (s: string) => (s === "autonomous" ? "◇" : "○");

const parseWita = (iso: string) => {
  if (!iso.endsWith("Z") && !iso.includes("+")) return new Date(iso + "Z");
  return new Date(iso);
};

const timeAgo = (iso: string) => {
  if (!iso) return "";
  const diff = Date.now() - parseWita(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "baru saja";
  if (mins < 60) return `${mins}m lalu`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}j lalu`;
  const days = Math.floor(hrs / 24);
  return `${days}h lalu`;
};

export default function ReportCard({
  id,
  title,
  source,
  priority,
  location,
  issue_type,
  narrative_preview,
  created_at,
}: ReportCardProps) {
  const router = useRouter();

  return (
    <motion.button
      onClick={() => router.push(`/laporan/${id}`)}
      className={cn(
        "w-full text-left px-5 py-4 rounded-lg",
        "bg-[var(--pemali-surface)] border border-[var(--pemali-border)]",
        "hover:bg-[#E8E4DC] transition-colors duration-200",
        "group"
      )}
      whileHover={{ y: -1 }}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.0, 0.0, 0.2, 1] }}
    >
      {/* Top row: priority dot + title */}
      <div className="flex items-start gap-3 mb-2">
        <span
          className="mt-[3px] w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: priorityColor(priority) }}
        />
        <div>
          <h3 className="text-[15px] font-[500] text-[var(--pemali-text-primary)] leading-snug group-hover:text-[var(--pemali-accent)] transition-colors">
            {title || issue_type || "Laporan Audit"}
          </h3>
          {location && (
            <span className="text-[12px] text-[var(--pemali-text-muted)] mt-0.5 block">
              {location}
            </span>
          )}
        </div>
      </div>

      {/* Preview */}
      {narrative_preview && (
        <p className="text-[13px] text-[var(--pemali-text-secondary)] leading-relaxed line-clamp-2 mb-3">
          {narrative_preview}
        </p>
      )}

      {/* Bottom row: meta */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Priority badge */}
        <span
          className="text-[11px] px-2 py-0.5 rounded-full font-[500]"
          style={{
            backgroundColor: `${priorityColor(priority)}16`,
            color: priorityColor(priority),
          }}
        >
          {priorityLabel(priority)} P{priority}
        </span>

        {/* Source badge */}
        <span className="text-[11px] text-[var(--pemali-text-muted)] font-mono flex items-center gap-1">
          <span>{sourceIcon(source)}</span>
          <span>{sourceLabel(source)}</span>
        </span>

        {/* Time */}
        <span className="text-[11px] text-[var(--pemali-text-muted)] font-mono ml-auto">
          {timeAgo(created_at)}
        </span>
      </div>
    </motion.button>
  );
}
