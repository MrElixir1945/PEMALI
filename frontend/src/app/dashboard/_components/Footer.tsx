"use client";

import { useTelemetryStore } from "@/stores/telemetryStore";
import { C } from "./shared";

export default function Footer() {
  const activeTraceId = useTelemetryStore((s) => s.activeTraceId);

  return (
    <div style={{
      display: "flex", justifyContent: "space-between", padding: "4px 16px",
      fontSize: 9, color: C.textMuted, letterSpacing: "0.06em",
      background: C.surface, borderTop: `0.5px solid ${C.border}`, flexShrink: 0,
    }}>
      <span>Tim Subak Guardian &middot; 2026</span>
      {activeTraceId && <span>trace: {activeTraceId}</span>}
    </div>
  );
}
