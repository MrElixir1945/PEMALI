"use client";

import { useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { TelemetryEvent } from "@/stores/telemetryStore";
import type { NodeState } from "./shared";
import { C, extractPhases, computeProgress } from "./shared";
import { StateBadge, NodeIconBadge } from "./shared";
import PhaseChain from "./PhaseChain";
import ProgressBar from "./ProgressBar";

export default function ManagerCompoundCard({ events }: { events: TelemetryEvent[] }) {
  const managerEvents = useMemo(
    () => events.filter((e) => e.node_id === "manager"), [events]
  );
  const latest = managerEvents[managerEvents.length - 1];
  const latestThinking = useMemo(
    () => [...managerEvents].reverse().find((e) => e.state === "THINKING"), [managerEvents]
  );
  const phases = useMemo(() => extractPhases(events), [events]);
  const activePhase = latest?.metadata?.phase as string | undefined;
  const { current, total } = useMemo(() => computeProgress(events), [events]);

  if (managerEvents.length === 0) return null;

  const currentState: NodeState = latest?.state ?? "IDLE";

  return (
    <div style={{
      background: C.white, border: `0.5px solid ${C.border}`,
      borderRadius: 10, overflow: "hidden", flexShrink: 0,
      boxShadow: "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)",
    }}>
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "9px 14px 8px", borderBottom: `0.5px solid ${C.borderLight}`,
      }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 7,
          fontSize: 11, fontWeight: 500, letterSpacing: "0.06em",
        }}>
          <NodeIconBadge nodeId="manager" size={20} />
          MANAGER
        </div>
        <StateBadge state={currentState} />
      </div>

      <PhaseChain segments={phases} activePhase={activePhase} />

      <AnimatePresence mode="wait">
        {latestThinking?.narrative && (
          <motion.div
            key={latestThinking.narrative.slice(0, 60)}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            transition={{ duration: 0.35, ease: [0, 0, 0.2, 1] }}
            style={{
              padding: "9px 14px", borderBottom: `0.5px solid ${C.borderLight}`,
              background: C.accentBg,
            }}
          >
            <div style={{
              fontSize: 9, letterSpacing: "0.10em", color: C.accent, marginBottom: 4,
            }}>
              THINKING
            </div>
            <div style={{ fontSize: 11, lineHeight: 1.65, color: "#3A3834" }}>
              {latestThinking.narrative}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <ProgressBar current={current} total={total} />
    </div>
  );
}
