"use client";

import { useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { TelemetryEvent } from "@/stores/telemetryStore";
import type { NodeState } from "./shared";
import { C, nodeLabel, getSubAgentIds } from "./shared";
import { StateBadge, NodeIconBadge, ShimmerBar } from "./shared";

function SubAgentCard({ agentId, events }: { agentId: string; events: TelemetryEvent[] }) {
  const agentEvents = useMemo(
    () => events.filter((e) => e.node_id === agentId), [events, agentId]
  );
  const latest = agentEvents[agentEvents.length - 1];
  const latestThinking = useMemo(
    () => [...agentEvents].reverse().find((e) => e.state === "THINKING"), [agentEvents]
  );
  const currentState: NodeState = latest?.state ?? "IDLE";
  const isExecuting = currentState === "EXECUTING";
  const isDone = currentState === "DONE";
  const isError = currentState === "ERROR";

  return (
    <div style={{
      background: C.white, border: `0.5px solid ${C.border}`, borderRadius: 8,
      padding: "8px 10px", display: "flex", flexDirection: "column", gap: 5,
      minWidth: 0, overflow: "hidden",
      boxShadow: "0 1px 2px rgba(0,0,0,0.03)",
    }}>
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between", gap: 4,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 5, minWidth: 0 }}>
          <NodeIconBadge nodeId={agentId} size={16} />
          <span style={{
            fontSize: 10, fontWeight: 500, letterSpacing: "0.06em",
            color: C.text, whiteSpace: "nowrap",
          }}>
            {nodeLabel(agentId)}
          </span>
        </div>
        <StateBadge state={currentState} />
      </div>

      <AnimatePresence mode="wait">
        {latestThinking?.narrative && (
          <motion.div
            key={latestThinking.narrative.slice(0, 40)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.22 }}
            style={{
              fontSize: 10, color: C.textSec, lineHeight: 1.45,
              display: "-webkit-box", WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical", overflow: "hidden",
            }}
          >
            {latestThinking.narrative}
          </motion.div>
        )}
      </AnimatePresence>

      <div style={{
        borderTop: `0.5px solid ${C.borderLight}`, paddingTop: 4, marginTop: 1,
      }}>
        {isExecuting && <ShimmerBar />}
        {isDone && (
          <span style={{ fontSize: 9, color: C.done, letterSpacing: "0.05em" }}>
            complete
          </span>
        )}
        {isError && (
          <span style={{ fontSize: 9, color: C.error, letterSpacing: "0.05em" }}>
            error
          </span>
        )}
        {!isExecuting && !isDone && !isError && (
          <span style={{ fontSize: 9, color: C.textMuted }}>
            {currentState.toLowerCase()}
          </span>
        )}
      </div>
    </div>
  );
}

export default function SubAgentGrid({ events }: { events: TelemetryEvent[] }) {
  const agentIds = useMemo(() => getSubAgentIds(events), [events]);

  if (agentIds.length === 0) {
    return (
      <div style={{
        background: C.white, border: `0.5px dashed ${C.border}`, borderRadius: 9,
        padding: "12px 14px", fontSize: 10, color: C.textMuted,
        letterSpacing: "0.05em", textAlign: "center",
        boxShadow: "0 1px 2px rgba(0,0,0,0.03)",
      }}>
        Waiting for agents to spawn...
      </div>
    );
  }

  const cols = Math.min(agentIds.length, 4);

  return (
    <div style={{
      display: "grid", gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`, gap: 6,
    }}>
      {agentIds.map((id) => (
        <SubAgentCard key={id} agentId={id} events={events} />
      ))}
    </div>
  );
}
