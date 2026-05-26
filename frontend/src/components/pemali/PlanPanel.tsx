"use client";

/* Direction: Dark Terminal Observatory — Plan Panel */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface CaseItem {
  case_id: string;
  title: string;
  priority: number;
  intent: string;
  urgency_reason: string;
}

interface PlanPanelProps {
  cases: CaseItem[];
}

const priorityColors: Record<string, string> = {
  high: "var(--state-error)",
  mid: "var(--state-thinking)",
  low: "var(--state-complete)",
};

function priorityBand(p: number): "high" | "mid" | "low" {
  if (p >= 8) return "high";
  if (p >= 5) return "mid";
  return "low";
}

function CaseRow({ c }: { c: CaseItem }) {
  const [expanded, setExpanded] = useState(false);
  const band = priorityBand(c.priority);
  const color = priorityColors[band];

  return (
    <motion.div
      className="border-b border-[var(--pemali-border)] last:border-b-0"
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2.5 px-0 py-2 text-left hover:bg-[var(--pemali-accent-dim)] rounded-sm transition-colors group"
      >
        <span
          className="text-[10px] font-mono font-[600] px-1.5 py-0.5 rounded flex-shrink-0"
          style={{ backgroundColor: `${color}18`, color }}
        >
          P{c.priority}
        </span>
        <span className="text-[13px] text-[var(--pemali-text-primary)] flex-1 leading-snug group-hover:text-[var(--pemali-accent)] transition-colors">
          {c.title}
        </span>
        <span className="text-[11px] font-mono text-[var(--pemali-text-muted)] transition-transform duration-200" style={{ transform: expanded ? "rotate(90deg)" : "rotate(0deg)" }}>
          &#8594;
        </span>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            className="pb-2 pl-10 pr-2 space-y-1"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: [0.0, 0.0, 0.2, 1] }}
          >
            <div className="text-[12px] text-[var(--pemali-text-secondary)] leading-relaxed">
              {c.intent}
            </div>
            <div className="text-[11px] font-mono text-[var(--pemali-text-muted)] leading-relaxed">
              {c.urgency_reason}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function PlanPanel({ cases }: PlanPanelProps) {
  if (!cases || cases.length === 0) return null;

  const priorities = cases.map((c) => c.priority);
  const minP = Math.min(...priorities);
  const maxP = Math.max(...priorities);

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[11px] font-mono font-[500] uppercase tracking-wider text-[var(--pemali-text-muted)]">
          Plan
        </span>
        <span className="text-[11px] font-mono text-[var(--pemali-text-muted)]">
          {cases.length} case{cases.length !== 1 ? "s" : ""}{" "}
          {priorities.length > 1 && (
            <>&middot; priorities P{maxP}&ndash;P{minP}</>
          )}
        </span>
      </div>
      <div className="border border-[var(--pemali-border)] rounded-lg px-3 bg-[var(--pemali-surface)]">
        {cases.map((c) => (
          <CaseRow key={c.case_id} c={c} />
        ))}
      </div>
    </div>
  );
}
