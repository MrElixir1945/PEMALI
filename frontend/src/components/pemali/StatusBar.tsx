"use client";

import { useTelemetryStore } from "@/stores/telemetryStore";

export default function StatusBar() {
  const isConnected = useTelemetryStore((s) => s.isConnected);

  return (
    <div className="border-b" style={{ borderColor: "var(--pemali-border)" }}>
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-2 flex items-center justify-between">
        <div className="flex items-center gap-4 text-[11px] font-mono" style={{ color: "var(--pemali-text-muted)" }}>
          <span>{process.env.NEXT_PUBLIC_OPENROUTER_MODEL || "deepseek/deepseek-v4-flash"}</span>
          <span className="hidden sm:inline">|</span>
          <span className="hidden sm:inline">worker: {isConnected ? "active" : "connecting..."}</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] font-mono" style={{ color: "var(--pemali-text-muted)" }}>
          <span className="relative flex h-1.5 w-1.5">
            {isConnected ? (
              <>
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ backgroundColor: "var(--state-executing)" }} />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5" style={{ backgroundColor: "var(--state-complete)" }} />
              </>
            ) : (
              <span className="relative inline-flex rounded-full h-1.5 w-1.5" style={{ backgroundColor: "var(--state-error)" }} />
            )}
          </span>
          <span>{isConnected ? "live" : "off"}</span>
        </div>
      </div>
    </div>
  );
}
