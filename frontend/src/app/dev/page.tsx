"use client";

/* Direction: Anthropic Terminal — Dev Dashboard */

import React from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import ModuleOutputDevPanel from "@/components/pemali/ModuleOutputDevPanel";

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.07, delayChildren: 0.1 },
  },
};

const item = {
  hidden: { opacity: 0, y: 16, filter: "blur(4px)" },
  show: {
    opacity: 1, y: 0, filter: "blur(0px)",
    transition: { duration: 0.5, ease: [0.0, 0.0, 0.2, 1] as const },
  },
};

export default function DevPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-[var(--pemali-bg)] text-[var(--pemali-text-primary)]">
      <motion.div
        className="max-w-4xl mx-auto px-5 py-12"
        variants={container}
        initial="hidden"
        animate="show"
      >
        {/* Back link */}
        <motion.button
          variants={item}
          onClick={() => router.push("/dashboard")}
          className="text-[12px] text-[var(--pemali-text-muted)] hover:text-[var(--pemali-text-primary)] transition-colors mb-6 inline-flex items-center gap-1 font-mono"
        >
          <span>←</span>
          <span>Dashboard</span>
        </motion.button>

        {/* Header */}
        <motion.div variants={item} className="mb-8">
          <h1 className="text-[28px] font-[500] tracking-[-0.02em] mb-2">
            Dev Dashboard
          </h1>
          <p className="text-[14px] text-[var(--pemali-text-secondary)] leading-relaxed">
            Live inspection module data dari SSE stream. Setiap event
            module <code className="text-[var(--pemali-accent)]">raw_payload</code>{" "}
            ditampilkan real-time untuk verifikasi data.
          </p>
        </motion.div>

        {/* Dev panel */}
        <motion.div variants={item}>
          <ModuleOutputDevPanel />
        </motion.div>
      </motion.div>
    </div>
  );
}
