"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";

const values = [
  { balinese: "Parahyangan", title: "Hubungan dengan Tuhan", desc: "Keseimbangan spiritual dalam setiap audit, memastikan teknologi selaras dengan nilai ketuhanan.", image: "/images/philosophy/Parahyangan.png" },
  { balinese: "Pawongan", title: "Hubungan dengan Sesama", desc: "Kolaborasi antar agent yang transparan. Setiap keputusan dapat ditelusuri dan dipertanggungjawabkan.", image: "/images/philosophy/Pawongan.png" },
  { balinese: "Palemahan", title: "Hubungan dengan Alam", desc: "Fokus utama pada kelestarian lingkungan Bali. Satelit memantau, AI menganalisis, alam terlindungi.", image: "/images/philosophy/palemahan.png" },
];

export default function PhilosophySection() {
  const headerRef = useRef(null);
  const headerInView = useInView(headerRef, { once: false, margin: "-100px" });

  const valueRefs = values.map(() => useRef(null));
  const valuesInView = valueRefs.map((ref) => useInView(ref, { once: false, margin: "-80px" }));

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
            <span className="text-sm italic" style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-muted)" }}>02</span>
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase" style={{ color: "var(--pemali-text-muted)" }}>——— Filosofi</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-medium mb-4" style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-primary)" }}>Dituntun oleh Nilai Leluhur</h2>
          <p className="text-base max-w-xl" style={{ color: "var(--pemali-text-muted)" }}>Setiap keputusan audit diambil berdasarkan tiga hubungan dasar dalam kehidupan Bali.</p>
        </motion.div>

        <div className="space-y-20 lg:space-y-32">
          {values.map((value, i) => {
            const isEven = i % 2 === 0;
            return (
              <motion.div
                key={value.balinese}
                ref={valueRefs[i]}
                initial={{ opacity: 0, y: 40 }}
                animate={valuesInView[i] ? { opacity: 1, y: 0 } : { opacity: 0, y: 40 }}
                transition={{ duration: 0.7, delay: 0.1, ease: [0.25, 0.1, 0.25, 1] as const }}
                className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-16 items-center"
              >
                <div className={`lg:col-span-7 ${isEven ? "lg:order-1" : "lg:order-2"}`}>
                  <div className={`flex items-center gap-3 mb-4 ${isEven ? "" : "lg:justify-end"}`}>
                    <span className="text-xs font-mono uppercase tracking-wider" style={{ color: "var(--pemali-text-muted)" }}>{value.balinese}</span>
                  </div>
                  <h3 className={`text-2xl md:text-3xl font-normal mb-4 ${isEven ? "" : "lg:text-right"}`} style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-primary)" }}>{value.title}</h3>
                  <p className={`text-base leading-relaxed max-w-md ${isEven ? "" : "lg:text-right lg:ml-auto"}`} style={{ color: "var(--pemali-text-secondary)" }}>{value.desc}</p>
                </div>

                <div className={`lg:col-span-5 ${isEven ? "lg:order-2" : "lg:order-1"}`}>
                  <div className={`aspect-[4/3] max-w-[360px] rounded-2xl border overflow-hidden ${isEven ? "lg:ml-auto" : "lg:mr-auto"}`} style={{ borderColor: "var(--pemali-border)", backgroundColor: "var(--pemali-surface)" }}>
                    <img src={value.image} alt={value.balinese} className="w-full h-full object-cover" />
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
