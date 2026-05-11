"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { CheckCircle, Loader2, XCircle } from "lucide-react";
import { useTelemetryStore, type TelemetryEvent } from "@/stores/telemetryStore";

function extractDagNodes(events: TelemetryEvent[]) {
  const nodeStates = new Map<string, string>();
  const order: string[] = [];

  for (const evt of events) {
    if (!nodeStates.has(evt.node_id)) {
      order.push(evt.node_id);
    }
    nodeStates.set(evt.node_id, evt.state);
  }

  return order.map((id) => ({
    id,
    label: id.replace(/_/g, " "),
    state: nodeStates.get(id) || "IDLE",
  }));
}

const stateColor: Record<string, string> = {
  IDLE: "var(--pemali-text-muted)",
  THINKING: "var(--state-thinking)",
  SPAWNING: "var(--state-spawning)",
  EXECUTING: "var(--state-executing)",
  DONE: "var(--state-complete)",
  ERROR: "var(--state-error)",
};

export default function DAGViewer() {
  const events = useTelemetryStore((s) => s.events);
  const nodes = useMemo(() => extractDagNodes(events), [events]);

  if (nodes.length === 0) return null;

  return (
    <div className="bg-[var(--pemali-surface)] rounded-2xl border border-[var(--pemali-border)] p-5">
      <div className="text-[9px] font-mono text-[var(--pemali-text-muted)] uppercase tracking-widest mb-4">
        Agent Pipeline — DAG
      </div>

      <div className="relative py-4">
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          {nodes.slice(0, -1).map((node, i) => (
            <line
              key={node.id}
              x1={`${((i + 0.8) / nodes.length) * 100}%`}
              y1="50%"
              x2={`${((i + 1.2) / nodes.length) * 100}%`}
              y2="50%"
              stroke={
                node.state === "DONE"
                  ? "var(--state-complete)"
                  : "var(--pemali-border)"
              }
              strokeWidth="1.5"
              strokeDasharray={node.state === "DONE" ? "0" : "4 4"}
            />
          ))}
        </svg>

        <div className="relative z-10 flex justify-between items-center">
          {nodes.map((node) => (
            <motion.div
              key={node.id}
              className="flex flex-col items-center gap-2"
              animate={{
                scale: node.state === "EXECUTING" ? [1, 1.05, 1] : 1,
              }}
              transition={{
                repeat: node.state === "EXECUTING" ? Infinity : 0,
                duration: 1.5,
              }}
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center border-2 transition-colors"
                style={{
                  borderColor: stateColor[node.state],
                  backgroundColor: `${stateColor[node.state]}15`,
                }}
              >
                {node.state === "DONE" ? (
                  <CheckCircle
                    className="w-5 h-5"
                    style={{ color: stateColor[node.state] }}
                  />
                ) : node.state === "ERROR" ? (
                  <XCircle
                    className="w-5 h-5"
                    style={{ color: stateColor[node.state] }}
                  />
                ) : node.state === "EXECUTING" || node.state === "THINKING" ? (
                  <Loader2
                    className="w-5 h-5 animate-spin"
                    style={{ color: stateColor[node.state] }}
                  />
                ) : (
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: stateColor[node.state] }}
                  />
                )}
              </div>
              <span
                className="text-[9px] font-mono uppercase tracking-widest"
                style={{ color: stateColor[node.state] }}
              >
                {node.label}
              </span>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
