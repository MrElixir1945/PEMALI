"use client";

/* Direction: Dark Terminal Observatory — Active Agent Run Cards */

import { motion, AnimatePresence } from "framer-motion";

interface AgentRun {
  caseId: string;
  title: string;
  priority: number;
  state: string;
  narrative: string;
}

interface ActiveRunsGridProps {
  runs: AgentRun[];
}

function priorityColor(p: number) {
  if (p >= 8) return "var(--state-error)";
  if (p >= 5) return "var(--state-thinking)";
  return "var(--state-complete)";
}

function stateColor(s: string) {
  switch (s) {
    case "SPAWNING":  return "var(--state-spawning)";
    case "EXECUTING": return "var(--state-executing)";
    case "DONE":      return "var(--state-complete)";
    case "ERROR":     return "var(--state-error)";
    default:          return "var(--state-thinking)";
  }
}

export default function ActiveRunsGrid({ runs }: ActiveRunsGridProps) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[11px] font-mono font-[500] uppercase tracking-wider text-[var(--pemali-text-muted)]">
          Active Runs
        </span>
        {runs.length > 0 && (
          <span className="text-[11px] font-mono text-[var(--pemali-text-muted)] tabular-nums">
            {runs.length}
          </span>
        )}
      </div>

      {runs.length === 0 ? (
        <div className="border border-[var(--pemali-border)] rounded-lg px-3 py-6 text-center bg-[var(--pemali-surface)]">
          <p className="text-[12px] font-mono text-[var(--pemali-text-muted)]">
            No active runs
          </p>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <AnimatePresence>
            {runs.map((run) => {
              const pColor = priorityColor(run.priority);
              const sColor = stateColor(run.state);
              const isActive = run.state === "EXECUTING" || run.state === "SPAWNING";

              return (
                <motion.div
                  key={run.caseId}
                  className="flex-1 min-w-[160px] max-w-[220px] px-3 py-2.5 rounded-lg border bg-[var(--pemali-surface)]"
                  style={{ borderColor: `${pColor}30` }}
                  initial={{ opacity: 0, y: 8, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -8, scale: 0.96 }}
                  transition={{ duration: 0.35, ease: [0.0, 0.0, 0.2, 1] }}
                >
                  {/* Title row */}
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <motion.span
                      className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: sColor }}
                      animate={isActive ? { opacity: [0.3, 1, 0.3] } : {}}
                      transition={{ duration: 1.2, repeat: isActive ? Infinity : 0 }}
                    />
                    <span className="text-[12px] font-[500] text-[var(--pemali-text-primary)] truncate">
                      {run.title}
                    </span>
                  </div>

                  {/* Priority bar */}
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-[10px] font-mono font-[600] px-1 rounded" style={{ backgroundColor: `${pColor}18`, color: pColor }}>
                      P{run.priority}
                    </span>
                    <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ backgroundColor: "var(--pemali-border)" }}>
                      <motion.div
                        className="h-full rounded-full"
                        style={{ backgroundColor: pColor }}
                        initial={{ width: 0 }}
                        animate={{ width: run.state === "SPAWNING" ? "25%" : run.state === "EXECUTING" ? "60%" : "100%" }}
                        transition={{ duration: 0.6, ease: [0.0, 0.0, 0.2, 1] }}
                      />
                    </div>
                  </div>

                  {/* State row */}
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-[var(--pemali-text-muted)]">
                      {run.state === "SPAWNING" ? "starting..." : run.state === "EXECUTING" ? "running" : run.state === "DONE" ? "done" : run.state}
                    </span>
                    <span
                      className="text-[10px] font-mono px-1 rounded"
                      style={{ color: sColor }}
                    >
                      {run.state}
                    </span>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
