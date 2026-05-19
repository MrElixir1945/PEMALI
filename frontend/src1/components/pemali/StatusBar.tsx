"use client";

export default function StatusBar() {
  return (
    <div className="border-b" style={{ borderColor: "var(--pemali-border)" }}>
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-2 flex items-center justify-between">
        <div className="flex items-center gap-4 text-[11px] font-mono" style={{ color: "var(--pemali-text-muted)" }}>
          <span>deepseek/deepseek-r1</span>
          <span className="hidden sm:inline">|</span>
          <span className="hidden sm:inline">worker: active</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] font-mono" style={{ color: "var(--pemali-text-muted)" }}>
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ backgroundColor: "var(--state-executing)" }} />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5" style={{ backgroundColor: "var(--state-complete)" }} />
          </span>
          <span>live</span>
        </div>
      </div>
    </div>
  );
}
