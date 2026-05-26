"use client";

import { useTelemetryStore } from "@/stores/telemetryStore";
import { C } from "./shared";

export default function DashboardStatusBar({
  sidebarOpen,
  onToggleSidebar,
}: {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}) {
  const { isConnected, isStreaming, events, activeTraceId } = useTelemetryStore();

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 16px",
      height: 48,
      background: C.surface,
      borderBottom: `0.5px solid ${C.border}`,
      flexShrink: 0,
      gap: 12,
    }}>
      {/* Left: toggle + logo */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button
          onClick={onToggleSidebar}
          style={{
            width: 28,
            height: 28,
            borderRadius: 6,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "transparent",
            border: `0.5px solid ${C.border}`,
            color: C.textSec,
            cursor: "pointer",
            fontSize: 13,
            transition: "all 0.15s",
          }}
          title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
        >
          {sidebarOpen ? "\u2715" : "\u2630"}
        </button>

        <span style={{
          fontFamily: "var(--font-lora), Georgia, serif",
          fontSize: 15,
          fontWeight: 500,
          color: C.text,
          letterSpacing: "0.01em",
        }}>
          PEMALI
        </span>
      </div>

      {/* Right: status indicators */}
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <span style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          fontSize: 10,
          color: C.textSec,
          letterSpacing: "0.03em",
        }}>
          <span style={{
            display: "inline-block",
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: isConnected ? C.done : C.textMuted,
            animation: isConnected ? "status-pulse 2s ease-in-out infinite" : "none",
          }} />
          {isConnected ? "connected" : "idle"}
        </span>

        {isStreaming && (
          <span style={{
            background: C.accentBg,
            color: "#9B6B42",
            padding: "2px 8px",
            borderRadius: 4,
            fontSize: 9,
            letterSpacing: "0.08em",
            fontWeight: 500,
            border: `0.5px solid ${C.accentBorder}`,
          }}>
            STREAMING
          </span>
        )}

        <span className="hidden sm:inline" style={{
          fontSize: 10,
          color: C.textMuted,
          letterSpacing: "0.03em",
        }}>
          {events.length} events
        </span>

        {activeTraceId && (
          <span style={{
            fontSize: 9,
            color: C.textMuted,
            fontFamily: "var(--font-geist-mono), monospace",
          }}>
            {activeTraceId.slice(0, 10)}
          </span>
        )}
      </div>
    </div>
  );
}
