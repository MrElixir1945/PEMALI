"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import Link from "next/link";

export default function CTASection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: false, margin: "-100px" });

  return (
    <section className="py-24 lg:py-32 border-t" style={{ borderColor: "var(--pemali-border)" }}>
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.7, ease: [0.25, 0.1, 0.25, 1] as const }}
          className="max-w-2xl"
        >
          <div className="flex items-center gap-3 mb-6">
            <span className="text-sm italic" style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-muted)" }}>05</span>
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase" style={{ color: "var(--pemali-text-muted)" }}>——— Mulai</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-medium mb-6" style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-primary)" }}>Siap menjaga keseimbangan alam Bali?</h2>
          <p className="text-base mb-10 leading-relaxed" style={{ color: "var(--pemali-text-muted)" }}>Bergabung dengan ekosistem agent yang bekerja 24/7 untuk memantau dan melindungi bentang alam Bali berdasarkan nilai-nilai Tri Hita Karana.</p>
          <div className="flex flex-col sm:flex-row gap-4">
            <Link href="/dashboard" className="inline-flex items-center px-8 py-4 rounded-lg text-sm font-medium transition-all group" style={{ backgroundColor: "var(--pemali-text-primary)", color: "var(--pemali-bg)" }}>
              Mulai Audit Sekarang
              <span className="ml-2 inline-block transition-transform group-hover:translate-x-0.5">&rarr;</span>
            </Link>
            <Link href="/monitor" className="inline-flex items-center px-8 py-4 rounded-lg text-sm font-medium transition-all border" style={{ borderColor: "var(--pemali-border)", color: "var(--pemali-text-secondary)" }}>
              Buka Ruang Pemantauan
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
