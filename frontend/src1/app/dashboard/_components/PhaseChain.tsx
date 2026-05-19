"use client";

import React, { useMemo } from "react";
import type { PhaseSegment } from "./shared";
import { C } from "./shared";

const PHASE_ORDER = ["planning", "execute", "validate", "synthesis", "done"];

export default function PhaseChain({
  segments,
  activePhase,
}: {
  segments: PhaseSegment[];
  activePhase: string | undefined;
}) {
  const allPhases = useMemo(() => {
    const base = [...PHASE_ORDER];
    for (const seg of segments) {
      if (seg.phase.startsWith("execute(") && !base.includes(seg.phase)) {
        const idx = base.indexOf("execute");
        base.splice(idx + 1, 0, seg.phase);
      }
    }
    return base.map((p) => {
      const seg = segments.find((s) => s.phase === p);
      return { phase: p, label: seg?.label ?? p, present: !!seg };
    });
  }, [segments]);

  const activeIdx = PHASE_ORDER.indexOf(activePhase ?? "");

  return (
    <div style={{
      display: "flex", alignItems: "center", padding: "8px 14px", gap: 0,
      borderBottom: `0.5px solid ${C.borderLight}`, overflowX: "auto", flexShrink: 0,
    }}>
      {allPhases.map((p, i) => {
        const pIdx = PHASE_ORDER.indexOf(p.phase);
        const isActive = p.phase === activePhase;
        const isDone = p.present && !isActive && pIdx < activeIdx;
        const color = isDone ? C.done : isActive ? C.accent : C.textMuted;
        return (
          <React.Fragment key={p.phase}>
            {i > 0 && (
              <div style={{
                width: 16, height: 1, flexShrink: 0,
                background: isDone ? "rgba(128,168,136,0.45)" : "rgba(26,25,20,0.12)",
              }} />
            )}
            <div style={{ display: "flex", alignItems: "center", gap: 4, flexShrink: 0 }}>
              <div style={{
                width: 6, height: 6, borderRadius: "50%",
                border: `1.5px solid ${color}`,
                background: isDone || isActive ? color : "transparent",
                transition: "all 0.3s ease",
              }} />
              <span style={{
                fontSize: 10, color, letterSpacing: "0.04em",
                whiteSpace: "nowrap", transition: "color 0.3s ease",
              }}>
                {p.label}
              </span>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
}
