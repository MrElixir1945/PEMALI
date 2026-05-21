"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";

const leftItems = [
  {
    label: "Multisource Fusion",
    title: "Multimodal Sensing",
    desc: "Mengintegrasikan citra satelit, data sensor, dan laporan warga untuk pengawasan bentang alam Bali secara menyeluruh.",
  },
  {
    label: "Real-time Stream",
    title: "Live Telemetry",
    desc: "Setiap langkah agent dipancarkan secara real-time ke dashboard melalui SSE, memberikan visibilitas penuh proses audit.",
  },
];

const rightItems = [
  {
    label: "DAG Orchestration",
    title: "Multi-Agent Orchestration",
    desc: "Manager Agent mendelegasikan tugas ke sub-agents melalui Directed Acyclic Graph, memungkinkan eksekusi paralel dan analisis multidimensi.",
  },
  {
    label: "Tri Hita Karana",
    title: "THK-Aligned Governance",
    desc: "Setiap keputusan diverifikasi terhadap nilai Parahyangan, Pawongan, dan Palemahan — teknologi selaras kearifan lokal Bali.",
  },
];

function FeatureCard({ item, alignRight }: { item: typeof leftItems[0]; alignRight: boolean }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: false, margin: "-80px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={inView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
      transition={{ duration: 0.6, ease: [0.25, 0.1, 0.25, 1] as const }}
      className={`flex flex-col gap-3 ${alignRight ? "items-end text-right" : "items-start text-left"}`}
    >
      <span className="text-xs font-mono uppercase tracking-wider" style={{ color: "var(--pemali-text-muted)" }}>
        {item.label}
      </span>
      <h3 className="text-xl md:text-2xl font-normal" style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-primary)" }}>
        {item.title}
      </h3>
      <p className={`text-sm leading-relaxed ${alignRight ? "text-right" : "text-left"}`} style={{ color: "var(--pemali-text-secondary)", maxWidth: "360px" }}>
        {item.desc}
      </p>
    </motion.div>
  );
}

export default function AppExplanationSection() {
  const headerRef = useRef(null);
  const headerInView = useInView(headerRef, { once: false, margin: "-100px" });

  return (
    <section className="py-24 lg:py-32 border-t" style={{ borderColor: "var(--pemali-border)" }}>
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          ref={headerRef}
          initial={{ opacity: 0, y: 30 }}
          animate={headerInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.7, ease: [0.25, 0.1, 0.25, 1] as const }}
          className="mb-20 text-center"
        >
          <div className="flex items-center justify-center gap-3 mb-6">
            <span className="text-sm italic" style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-muted)" }}>01</span>
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase" style={{ color: "var(--pemali-text-muted)" }}>——— Platform</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-medium mb-4" style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-primary)" }}>Apa itu PEMALI?</h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--pemali-text-muted)" }}>
            Platform audit lingkungan otonom berbasis Agentic AI yang memantau, menganalisis, dan melaporkan kondisi ekologi Bali secara real-time.
          </p>
        </motion.div>

        <div className="relative grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20">
          {/* Vertical divider line */}
          <div className="hidden lg:block absolute left-1/2 top-0 bottom-0 w-px -translate-x-1/2" style={{ backgroundColor: "var(--pemali-border)" }} />

          {/* Left column */}
          <div className="flex flex-col gap-16 lg:pr-12">
            {leftItems.map((item) => (
              <FeatureCard key={item.title} item={item} alignRight />
            ))}
          </div>

          {/* Right column */}
          <div className="flex flex-col gap-16 lg:pl-12">
            {rightItems.map((item) => (
              <FeatureCard key={item.title} item={item} alignRight={false} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
