"use client";

/* Direction: Refined Anthropic Editorial — Autonomous Swarm */

import React from "react";
import { motion } from "framer-motion";
import AutonomousSwarmPanel from "@/components/pemali/AutonomousSwarmPanel";
import NavBar from "@/components/NavBar";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06, delayChildren: 0.08 } }
};

const item = {
  hidden: { opacity: 0, y: 10, filter: "blur(2px)" },
  show: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.45, ease: [0.0, 0.0, 0.2, 1] as const } }
};

export default function AgenticPage() {
  return (
    <>
      <NavBar />
      <motion.div
        className="min-h-[calc(100vh-56px)] flex flex-col relative"
        style={{
          backgroundColor: "#F5F4EF",
          color: "#1A1916",
          fontFamily: "var(--font-geist-sans), system-ui, sans-serif",
        }}
        variants={container}
        initial="hidden"
        animate="show"
      >
        {/* Subtle grid overlay */}
        <div
          className="absolute inset-0 pointer-events-none z-0"
          style={{
            backgroundImage: `linear-gradient(rgba(26,25,22,0.015) 1px, transparent 1px), linear-gradient(90deg, rgba(26,25,22,0.015) 1px, transparent 1px)`,
            backgroundSize: "32px 32px",
          }}
        />

        <div className="relative z-10 flex-1 flex flex-col max-w-5xl mx-auto w-full px-6 lg:px-8 py-10 min-h-0">
          {/* Header */}
          <motion.div variants={item} className="mb-6 flex-shrink-0">
            <div className="text-[11px] font-mono uppercase tracking-[0.15em] mb-2" style={{ color: "#888780" }}>
              01 ——— AGENTIC SWARM PORTAL
            </div>
            <h1 className="font-serif text-[38px] font-light tracking-tight text-[#1A1916] leading-tight mb-2">
              Siklus Otonom PEMALI
            </h1>
            <p className="text-[13px] text-[#5F5E5A] leading-relaxed max-w-2xl">
              Memantau dan mengaudit ekologi Bali secara terus-menerus. Manager Agent dan Sub-Agent bekerja secara mandiri
              untuk mengidentifikasi pelanggaran, menganalisis bencana, dan menyusun laporan audit yang komprehensif.
            </p>
          </motion.div>

          <motion.main className="flex-1 min-h-0 flex flex-col bg-[#FCFAF6] border border-[rgba(26,25,22,0.08)] rounded-2xl p-6 shadow-[0_8px_30px_rgba(26,25,22,0.02)]" style={{ overflow: "hidden" }} variants={item}>
            <AutonomousSwarmPanel />
          </motion.main>
        </div>
      </motion.div>
    </>
  );
}
