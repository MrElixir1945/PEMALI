"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";

const observationItems = [
  { image: "/images/architecture/items/dag.png", label: "DAG Visualizer" },
  { image: "/images/architecture/items/timeline.png", label: "Agent State Timeline" },
  { image: "/images/architecture/items/sse.png", label: "SSE Telemetry Stream" },
  { image: "/images/architecture/items/module.png", label: "Module Output Cards" },
];

const interactionItems = [
  { image: "/images/architecture/items/chat.png", label: "Chat Input" },
  { image: "/images/architecture/items/history.png", label: "Task History" },
  { image: "/images/architecture/items/trigger.png", label: "Trigger Button" },
];

export default function ArchitectureSection() {
  const headerRef = useRef(null);
  const headerInView = useInView(headerRef, { once: false, margin: "-100px" });

  const obsRef = useRef(null);
  const obsInView = useInView(obsRef, { once: false, margin: "-60px" });

  const intRef = useRef(null);
  const intInView = useInView(intRef, { once: false, margin: "-60px" });

  const obsItemRefs = observationItems.map(() => useRef(null));
  const obsItemsInView = obsItemRefs.map((ref) => useInView(ref, { once: false, margin: "-40px" }));

  const intItemRefs = interactionItems.map(() => useRef(null));
  const intItemsInView = intItemRefs.map((ref) => useInView(ref, { once: false, margin: "-40px" }));

  return (
    <section className="py-24 lg:py-32 border-t" style={{ borderColor: "var(--pemali-border)" }}>
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          ref={headerRef}
          initial={{ opacity: 0, y: 30 }}
          animate={headerInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.7, ease: [0.25, 0.1, 0.25, 1] as const }}
          className="mb-20"
        >
          <div className="flex items-center gap-3 mb-6">
            <span className="text-sm italic" style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-muted)" }}>04</span>
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase" style={{ color: "var(--pemali-text-muted)" }}>——— Arsitektur</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-medium mb-4" style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-primary)" }}>Arsitektur Dua Zona</h2>
          <p className="text-base max-w-xl" style={{ color: "var(--pemali-text-muted)" }}>Dashboard PEMALI dibagi menjadi dua zona fungsional yang saling melengkapi.</p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <motion.div
            ref={obsRef}
            initial={{ opacity: 0, y: 30 }}
            animate={obsInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.7, ease: [0.25, 0.1, 0.25, 1] as const }}
            className="lg:col-span-3"
          >
            <div className="h-full p-8 rounded-xl border" style={{ borderColor: "var(--pemali-border)", backgroundColor: "var(--pemali-surface)" }}>
              <div className="flex items-center gap-3 mb-8">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "var(--state-executing)" }} />
                <span className="text-xs font-mono uppercase tracking-wider" style={{ color: "var(--pemali-text-muted)" }}>Observation Zone</span>
                <span className="text-xs font-mono ml-auto" style={{ color: "var(--pemali-text-muted)" }}>60%</span>
              </div>
              <div className="mb-6 rounded-xl overflow-hidden border-2 flex items-center justify-center" style={{ borderColor: "var(--pemali-border)", backgroundColor: "#EDE5D8" }}>
                <img src="/images/architecture/observation.png" alt="Observation Zone" className="w-full h-48 object-contain scale-105" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                {observationItems.map((item, i) => (
                  <motion.div
                    key={item.label}
                    ref={obsItemRefs[i]}
                    initial={{ opacity: 0, x: -10 }}
                    animate={obsItemsInView[i] ? { opacity: 1, x: 0 } : { opacity: 0, x: -10 }}
                    transition={{ duration: 0.5, delay: i * 0.1, ease: [0.25, 0.1, 0.25, 1] as const }}
                    className="flex items-center gap-3 p-4 rounded-lg"
                    style={{ backgroundColor: "var(--pemali-bg)" }}
                  >
                    <img src={item.image} alt={item.label} className="w-12 h-12 rounded-full object-cover" />
                    <span className="text-sm font-mono" style={{ color: "var(--pemali-text-secondary)" }}>{item.label}</span>
                  </motion.div>
                ))}
              </div>
              <div className="mt-8 pt-6 border-t" style={{ borderColor: "var(--pemali-border)" }}>
                <p className="text-sm leading-relaxed" style={{ color: "var(--pemali-text-muted)" }}>Zona ini menampilkan visualisasi DAG, timeline status agent, stream telemetry real-time, dan output dari modul sensor. Semua data ditampilkan secara live melalui koneksi SSE.</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            ref={intRef}
            initial={{ opacity: 0, y: 30 }}
            animate={intInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
            transition={{ duration: 0.7, delay: 0.15, ease: [0.25, 0.1, 0.25, 1] as const }}
            className="lg:col-span-2"
          >
            <div className="h-full p-8 rounded-xl border" style={{ borderColor: "var(--pemali-border)", backgroundColor: "var(--pemali-surface)" }}>
              <div className="flex items-center gap-3 mb-8">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "var(--state-spawning)" }} />
                <span className="text-xs font-mono uppercase tracking-wider" style={{ color: "var(--pemali-text-muted)" }}>Interaction Zone</span>
                <span className="text-xs font-mono ml-auto" style={{ color: "var(--pemali-text-muted)" }}>40%</span>
              </div>
              <div className="mb-6 rounded-xl overflow-hidden border-2 flex items-center justify-center" style={{ borderColor: "var(--pemali-border)", backgroundColor: "#EDE5D8" }}>
                <img src="/images/architecture/interaction.png" alt="Interaction Zone" className="w-full h-48 object-contain scale-125" />
              </div>
              <div className="space-y-3">
                {interactionItems.map((item, i) => (
                  <motion.div
                    key={item.label}
                    ref={intItemRefs[i]}
                    initial={{ opacity: 0, x: 10 }}
                    animate={intItemsInView[i] ? { opacity: 1, x: 0 } : { opacity: 0, x: 10 }}
                    transition={{ duration: 0.5, delay: 0.15 + i * 0.1, ease: [0.25, 0.1, 0.25, 1] as const }}
                    className="flex items-center gap-3 p-4 rounded-lg"
                    style={{ backgroundColor: "var(--pemali-bg)" }}
                  >
                    <img src={item.image} alt={item.label} className="w-12 h-12 rounded-full object-cover" />
                    <span className="text-sm font-mono" style={{ color: "var(--pemali-text-secondary)" }}>{item.label}</span>
                  </motion.div>
                ))}
              </div>
              <div className="mt-8 pt-6 border-t" style={{ borderColor: "var(--pemali-border)" }}>
                <p className="text-sm leading-relaxed" style={{ color: "var(--pemali-text-muted)" }}>Zona interaksi untuk memberikan perintah, melihat riwayat tugas, dan memicu audit manual. Titik sentuh antara manusia dan agent.</p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
