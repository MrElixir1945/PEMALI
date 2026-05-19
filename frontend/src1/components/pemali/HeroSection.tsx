"use client";

import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import Link from "next/link";

const Terminal = dynamic(() => import("@/components/Terminal"), {
  ssr: false,
  loading: () => (
    <div className="rounded-3xl border overflow-hidden h-[340px] flex flex-col" style={{ backgroundColor: "var(--pemali-surface)", borderColor: "var(--pemali-border)" }}>
      <div className="px-6 py-4 flex items-center border-b" style={{ borderColor: "var(--pemali-border)" }}>
        <div className="flex space-x-1.5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: "var(--pemali-text-muted)" }} />
          ))}
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-pulse font-mono text-xs" style={{ color: "var(--pemali-text-muted)" }}>Initializing...</div>
      </div>
    </div>
  ),
});

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.15 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20, filter: "blur(4px)" },
  show: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.7, ease: [0.25, 0.1, 0.25, 1] as const } },
};

export default function HeroSection() {
  return (
    <section className="relative pt-16 pb-24 lg:pb-32 overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          <motion.div className="lg:col-span-7" variants={containerVariants} initial="hidden" animate="show">
            <motion.div variants={itemVariants}>
              <div className="flex items-center gap-3 mb-8">
                <span className="text-sm italic" style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-muted)" }}>01</span>
                <span className="text-[10px] font-mono tracking-[0.2em] uppercase" style={{ color: "var(--pemali-text-muted)" }}>——— Tentang</span>
              </div>
            </motion.div>

            <motion.h1 variants={itemVariants} className="text-5xl md:text-7xl lg:text-8xl font-normal leading-[1.05] tracking-tight mb-6" style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-primary)" }}>
              PEMALI
            </motion.h1>

            <motion.p variants={itemVariants} className="text-xl md:text-2xl font-normal mb-6 max-w-lg" style={{ color: "var(--pemali-text-secondary)" }}>
              Platform Ekologi Modular Agentic berbasis Artificial Intelligence
            </motion.p>

            <motion.p variants={itemVariants} className="text-base leading-relaxed mb-10 max-w-xl" style={{ color: "var(--pemali-text-muted)" }}>
              Sistem peringatan dini digital yang menjaga keseimbangan alam Bali berdasarkan filosofi Tri Hita Karana. Mengintegrasikan citra satelit dan Agentic AI untuk pengawasan bentang alam secara real-time.
            </motion.p>

            <motion.div variants={itemVariants} className="flex flex-col sm:flex-row items-start gap-4">
              <Link href="/dashboard" className="px-6 py-3 rounded-lg text-sm font-medium transition-all flex items-center group" style={{ backgroundColor: "var(--pemali-text-primary)", color: "var(--pemali-bg)" }}>
                Mulai Audit Sekarang
                <span className="ml-1.5 inline-block transition-transform group-hover:translate-x-0.5">&rarr;</span>
              </Link>
              <Link href="/methodology" className="px-6 py-3 rounded-lg text-sm font-medium transition-all flex items-center border" style={{ borderColor: "var(--pemali-border)", color: "var(--pemali-text-secondary)" }}>
                Pelajari Metodologi
              </Link>
            </motion.div>

            <motion.div variants={itemVariants} className="mt-12 pt-6 border-t flex items-center gap-8" style={{ borderColor: "var(--pemali-border)" }}>
              <div><div className="text-2xl font-mono" style={{ color: "var(--pemali-text-primary)" }}>3+</div><div className="text-xs font-mono" style={{ color: "var(--pemali-text-muted)" }}>Sub-Agents</div></div>
              <div className="w-px h-8" style={{ backgroundColor: "var(--pemali-border)" }} />
              <div><div className="text-2xl font-mono" style={{ color: "var(--pemali-text-primary)" }}>Real-time</div><div className="text-xs font-mono" style={{ color: "var(--pemali-text-muted)" }}>Satellite Feed</div></div>
              <div className="w-px h-8" style={{ backgroundColor: "var(--pemali-border)" }} />
              <div><div className="text-2xl font-mono" style={{ color: "var(--pemali-text-primary)" }}>THK</div><div className="text-xs font-mono" style={{ color: "var(--pemali-text-muted)" }}>Aligned</div></div>
            </motion.div>
          </motion.div>

          <motion.div className="lg:col-span-5" initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.8, delay: 0.5, ease: [0.25, 0.1, 0.25, 1] as const }}>
            <Terminal />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
