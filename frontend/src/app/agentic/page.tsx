"use client";

/* Direction: Refined Anthropic Editorial — Autonomous Swarm */

import React from "react";
import { useRouter } from "next/navigation";
import NarrativeStream from "@/components/pemali/NarrativeStream";
import AutonomousSwarmPanel from "@/components/pemali/AutonomousSwarmPanel";

export default function AgenticPage() {
  const router = useRouter();

  return (
    <div
      className="h-screen overflow-hidden relative"
      style={{
        background: "#F5F4EF",
        color: "#1A1916",
        fontFamily: "var(--font-geist-sans), system-ui, sans-serif",
      }}
    >
      {/* Subtle grain — CSS noise, very faint */}
      <div
        className="absolute inset-0 pointer-events-none z-0 opacity-[0.015]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='200' height='200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
          backgroundSize: "200px 200px",
        }}
      />

      <NarrativeStream />

      <div className="relative z-10 h-full flex flex-col">
        {/* Header */}
        <header className="flex-shrink-0 px-8 pt-5 pb-0">
          <button
            onClick={() => router.push("/dashboard")}
            className="text-[11px] tracking-wide font-mono mb-2 opacity-40 hover:opacity-70 transition-opacity block"
            style={{ color: "#7A7670", fontFamily: "var(--font-geist-mono), monospace" }}
          >
            &larr; Dashboard
          </button>

          <h1
            className="text-[28px] font-normal leading-tight tracking-[-0.02em] mb-1"
            style={{ fontFamily: "var(--font-lora), Georgia, serif", color: "#1A1916" }}
          >
            Autonomous Swarm
          </h1>
          <p
            className="text-[13px] leading-relaxed max-w-[480px]"
            style={{ color: "#7A7670" }}
          >
            Agent Otak memantau Bali secara otonom &mdash; memutuskan kasus,
            menjalankan audit, dan menjadwalkan siklus berikutnya tanpa
            campur tangan manusia.
          </p>
        </header>

        {/* Hairline */}
        <div className="flex-shrink-0 mx-8 mt-3 mb-0" style={{ height: "1px", background: "rgba(26,25,22,0.07)" }} />

        {/* Main content */}
        <main className="flex-1 min-h-0 px-8 py-2" style={{ overflow: "hidden" }}>
          <AutonomousSwarmPanel />
        </main>
      </div>
    </div>
  );
}
