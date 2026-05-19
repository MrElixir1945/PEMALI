"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";

const steps = [
  { title: "Pemicu", desc: "Perubahan data satelit atau jadwal rutin memicu agent untuk memulai audit.", icon: "/images/pemicu.png" },
  { title: "Pemikiran", desc: "Agent menganalisis data awal dan menentukan modul sensor mana yang diperlukan.", icon: "/images/pemikiran.png" },
  { title: "Aksi", desc: "Agent mengirimkan JSON call melalui Communicate Layer ke modul yang terpilih.", icon: "/images/aksi.png" },
  { title: "Observasi", desc: "Agent menerima hasil, memperbarui memori, dan memutuskan langkah selanjutnya.", icon: "/images/observasi.png" },
];

export default function LoopSection() {
  const headerRef = useRef(null);
  const headerInView = useInView(headerRef, { once: false, margin: "-100px" });

  const lineRef = useRef(null);
  const lineInView = useInView(lineRef, { once: false, margin: "-60px" });

  const stepRefs = steps.map(() => useRef(null));
  const stepsInView = stepRefs.map((ref) => useInView(ref, { once: false, margin: "-60px" }));

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
            <span className="text-sm italic" style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-muted)" }}>03</span>
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase" style={{ color: "var(--pemali-text-muted)" }}>——— Cara Kerja</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-medium mb-4" style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-primary)" }}>Siklus Otonom</h2>
          <p className="text-base max-w-xl" style={{ color: "var(--pemali-text-muted)" }}>PEMALI bekerja secara mandiri dalam empat langkah berkelanjutan.</p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 relative">
          <motion.div 
            ref={lineRef}
            initial={{ scaleX: 0, opacity: 0 }}
            animate={lineInView ? { scaleX: 1, opacity: 1 } : { scaleX: 0, opacity: 0 }}
            transition={{ duration: 0.8, delay: 0.2, ease: [0.25, 0.1, 0.25, 1] as const }}
            className="hidden lg:block absolute top-10 left-[12.5%] right-[12.5%] h-[2px] origin-left" 
            style={{ backgroundColor: "var(--pemali-border)" }} 
          />

          {steps.map((step, i) => (
            <motion.div
              key={step.title}
              ref={stepRefs[i]}
              initial={{ opacity: 0, y: 30 }}
              animate={stepsInView[i] ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
              transition={{ duration: 0.6, delay: i * 0.1, ease: [0.25, 0.1, 0.25, 1] as const }}
              className="relative text-center"
            >
              <div className="relative z-10 w-20 h-20 mx-auto mb-8 flex items-center justify-center">
                <img src={step.icon} alt={step.title} className="w-full h-full object-contain scale-150" />
              </div>
              <h3 className="text-xl font-medium mb-2" style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-primary)" }}>{step.title}</h3>
              <p className="text-sm leading-relaxed max-w-[220px] mx-auto" style={{ color: "var(--pemali-text-muted)" }}>{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
