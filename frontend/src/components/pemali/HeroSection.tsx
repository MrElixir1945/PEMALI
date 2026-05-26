"use client";

/* Direction: Refined Anthropic Editorial — Hero Section with Stationery Paper Frame */

import { motion } from "framer-motion";
import Link from "next/link";

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
            <motion.h1 variants={itemVariants} className="text-5xl md:text-7xl lg:text-8xl font-normal leading-[1.05] tracking-tight mb-6" style={{ fontFamily: "var(--font-lora)", color: "var(--pemali-text-primary)" }}>
              PEMALI
            </motion.h1>

            <motion.p variants={itemVariants} className="text-base md:text-lg font-normal mb-6 max-w-2xl leading-relaxed" style={{ color: "var(--pemali-text-secondary)" }}>
              Inovasi Platform Audit Lingkungan Berbasis Artificial Intelligence dalam Mendukung Kelestarian Bali di Era Transformasi Digital
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
              <div><div className="text-2xl font-mono" style={{ color: "var(--pemali-text-primary)" }}>8+</div><div className="text-xs font-mono" style={{ color: "var(--pemali-text-muted)" }}>Sub-Agents</div></div>
              <div className="w-px h-8" style={{ backgroundColor: "var(--pemali-border)" }} />
              <div><div className="text-2xl font-mono" style={{ color: "var(--pemali-text-primary)" }}>Real-time</div><div className="text-xs font-mono" style={{ color: "var(--pemali-text-muted)" }}>Satellite Feed</div></div>
              <div className="w-px h-8" style={{ backgroundColor: "var(--pemali-border)" }} />
              <div><div className="text-2xl font-mono" style={{ color: "var(--pemali-text-primary)" }}>THK</div><div className="text-xs font-mono" style={{ color: "var(--pemali-text-muted)" }}>Aligned</div></div>
            </motion.div>
          </motion.div>

          <motion.div className="lg:col-span-5" initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.8, delay: 0.5, ease: [0.25, 0.1, 0.25, 1] as const }}>
            {/* Stationery Paper Card Frame */}
            <div 
              className="rounded-2xl border border-stone-300/70 bg-[#FAF9F5] p-5 shadow-sm relative overflow-hidden flex flex-col gap-4"
              style={{
                fontFamily: "var(--font-geist-sans), system-ui, sans-serif",
              }}
            >
              {/* Ultra-subtle paper grain overlay */}
              <div 
                className="absolute inset-0 pointer-events-none opacity-[0.03]"
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`
                }}
              />

              {/* Monospace Header */}
              <div className="flex items-center justify-between border-b border-stone-200 pb-2.5 flex-shrink-0 z-10">
                <span className="text-[10px] font-mono tracking-wider text-[var(--pemali-text-muted)] uppercase">
                  Fig. A1 // PEMALI Ecological Unit
                </span>
                <span className="text-[9px] font-mono text-[var(--pemali-text-muted)] uppercase tracking-widest bg-stone-200/50 px-1.5 py-0.5 rounded">
                  Hyperspectral
                </span>
              </div>

              {/* Image Frame — with radar/scan overlay */}
              <div className="rounded-lg overflow-hidden border border-stone-200 bg-white shadow-[inset_0_1px_3px_rgba(0,0,0,0.02)] z-10 relative">
                <img 
                  src="/images/bali_satellite_analytics.png" 
                  alt="Bali Satellite Ecological Analytics" 
                  className="w-full h-auto object-contain"
                />

                {/* ── Radar / Scan Overlay ── */}
                <div className="absolute inset-0 pointer-events-none select-none" aria-hidden>
                  <svg
                    viewBox="0 0 400 300"
                    xmlns="http://www.w3.org/2000/svg"
                    className="absolute inset-0 w-full h-full"
                  >
                    <defs>
                      {/* Radial base glow */}
                      <radialGradient id="rg-base" cx="50%" cy="49.3%" r="38%">
                        <stop offset="0%"   stopColor="#0fba80" stopOpacity="0.22" />
                        <stop offset="60%"  stopColor="#0fba80" stopOpacity="0.07" />
                        <stop offset="100%" stopColor="#0fba80" stopOpacity="0"    />
                      </radialGradient>

                      {/* Sweep wedge — conic-like fill using multiple paths */}
                      <radialGradient id="rg-sweep" cx="0%" cy="50%" r="100%" gradientUnits="objectBoundingBox">
                        <stop offset="0%"   stopColor="#10b981" stopOpacity="0.65" />
                        <stop offset="100%" stopColor="#10b981" stopOpacity="0"    />
                      </radialGradient>

                      {/* Glow filter for leading arm */}
                      <filter id="glow-arm" x="-50%" y="-50%" width="200%" height="200%">
                        <feGaussianBlur stdDeviation="3" result="blur" />
                        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                      </filter>

                      {/* Glow filter for blips */}
                      <filter id="glow-blip" x="-100%" y="-100%" width="300%" height="300%">
                        <feGaussianBlur stdDeviation="2.5" result="blur" />
                        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                      </filter>

                      {/* Clip to radar circle */}
                      <clipPath id="rc">
                        <circle cx="200" cy="148" r="115" />
                      </clipPath>
                    </defs>

                    {/* Base ambient glow */}
                    <circle cx="200" cy="148" r="115" fill="url(#rg-base)" />

                    {/* ── Static reference grid rings ── */}
                    <circle cx="200" cy="148" r="38"  fill="none" stroke="#10b981" strokeWidth="0.7" strokeOpacity="0.3" strokeDasharray="3 5" />
                    <circle cx="200" cy="148" r="70"  fill="none" stroke="#10b981" strokeWidth="0.7" strokeOpacity="0.22" strokeDasharray="3 7" />
                    <circle cx="200" cy="148" r="105" fill="none" stroke="#10b981" strokeWidth="0.7" strokeOpacity="0.15" />

                    {/* ── Expanding ping rings ── */}
                    <circle cx="200" cy="148" r="0" fill="none" stroke="#10b981" strokeWidth="1.8" strokeOpacity="0.7">
                      <animate attributeName="r"             values="5;108"      dur="6s" begin="0s"    repeatCount="indefinite" />
                      <animate attributeName="stroke-opacity" values="0.7;0"     dur="6s" begin="0s"    repeatCount="indefinite" />
                      <animate attributeName="stroke-width"   values="1.8;0.3"   dur="6s" begin="0s"    repeatCount="indefinite" />
                    </circle>
                    <circle cx="200" cy="148" r="0" fill="none" stroke="#10b981" strokeWidth="1.8" strokeOpacity="0.7">
                      <animate attributeName="r"             values="5;108"      dur="6s" begin="-2s" repeatCount="indefinite" />
                      <animate attributeName="stroke-opacity" values="0.7;0"     dur="6s" begin="-2s" repeatCount="indefinite" />
                      <animate attributeName="stroke-width"   values="1.8;0.3"   dur="6s" begin="-2s" repeatCount="indefinite" />
                    </circle>
                    <circle cx="200" cy="148" r="0" fill="none" stroke="#10b981" strokeWidth="1.8" strokeOpacity="0.7">
                      <animate attributeName="r"             values="5;108"      dur="6s" begin="-4s" repeatCount="indefinite" />
                      <animate attributeName="stroke-opacity" values="0.7;0"     dur="6s" begin="-4s" repeatCount="indefinite" />
                      <animate attributeName="stroke-width"   values="1.8;0.3"   dur="6s" begin="-4s" repeatCount="indefinite" />
                    </circle>

                    {/* ── Rotating sweep arm (clipped to radar circle) ── */}
                    <g clipPath="url(#rc)">
                      <g>
                        <animateTransform
                          attributeName="transform"
                          type="rotate"
                          from="0 200 148"
                          to="360 200 148"
                          dur="8s"
                          repeatCount="indefinite"
                        />
                        {/* Trailing wedge — ~80° arc gradient */}
                        <path d="M200,148 L315,148 A115,115 0 0,0 279,68 Z"  fill="#10b981" fillOpacity="0.12" />
                        <path d="M200,148 L315,148 A115,115 0 0,0 340,100 Z" fill="#10b981" fillOpacity="0.09" />
                        <path d="M200,148 L315,148 A115,115 0 0,0 315,185 Z" fill="#10b981" fillOpacity="0.05" />

                        {/* Leading bright edge with glow */}
                        <line
                          x1="200" y1="148"
                          x2="315" y2="148"
                          stroke="#10b981"
                          strokeWidth="1.8"
                          strokeOpacity="0.9"
                          filter="url(#glow-arm)"
                        />
                        {/* Secondary softer line just behind */}
                        <line
                          x1="200" y1="148"
                          x2="315" y2="148"
                          stroke="#6ee7b7"
                          strokeWidth="0.5"
                          strokeOpacity="0.6"
                          filter="url(#glow-arm)"
                        />
                      </g>
                    </g>

                    {/* ── Crosshair center ── */}
                    <line x1="193" y1="148" x2="207" y2="148" stroke="#10b981" strokeWidth="0.8" strokeOpacity="0.6" />
                    <line x1="200" y1="141" x2="200" y2="155" stroke="#10b981" strokeWidth="0.8" strokeOpacity="0.6" />
                    <circle cx="200" cy="148" r="2.5" fill="#10b981" fillOpacity="0.8" filter="url(#glow-blip)">
                      <animate attributeName="fill-opacity" values="0.8;1;0.8" dur="1.5s" repeatCount="indefinite" />
                    </circle>

                    {/* ── Blip dots — locations on Bali ── */}
                    {/* Denpasar (SW) */}
                    <g filter="url(#glow-blip)">
                      <circle cx="215" cy="168" r="3.5" fill="#10b981" fillOpacity="0">
                        <animate attributeName="fill-opacity" values="0;0.9;0.9;0" dur="7s" begin="-1.5s" repeatCount="indefinite" />
                      </circle>
                      <circle cx="215" cy="168" r="7" fill="none" stroke="#10b981" strokeWidth="1" strokeOpacity="0">
                        <animate attributeName="r"             values="3;10"      dur="1.8s" begin="-1.5s" repeatCount="indefinite" />
                        <animate attributeName="stroke-opacity" values="0.7;0"   dur="1.8s" begin="-1.5s" repeatCount="indefinite" />
                      </circle>
                    </g>
                    {/* Kintamani — hotspot amber */}
                    <g filter="url(#glow-blip)">
                      <circle cx="200" cy="136" r="3" fill="#f59e0b" fillOpacity="0">
                        <animate attributeName="fill-opacity" values="0;1;1;0" dur="7s" begin="-3.5s" repeatCount="indefinite" />
                      </circle>
                      <circle cx="200" cy="136" r="6" fill="none" stroke="#f59e0b" strokeWidth="1" strokeOpacity="0">
                        <animate attributeName="r"             values="3;9"       dur="1.8s" begin="-3.5s" repeatCount="indefinite" />
                        <animate attributeName="stroke-opacity" values="0.8;0"   dur="1.8s" begin="-3.5s" repeatCount="indefinite" />
                      </circle>
                    </g>
                    {/* Ubud */}
                    <g filter="url(#glow-blip)">
                      <circle cx="207" cy="152" r="2.5" fill="#10b981" fillOpacity="0">
                        <animate attributeName="fill-opacity" values="0;0.85;0.85;0" dur="7s" begin="-0.6s" repeatCount="indefinite" />
                      </circle>
                    </g>
                    {/* Singaraja (N coast) */}
                    <g filter="url(#glow-blip)">
                      <circle cx="192" cy="122" r="2" fill="#10b981" fillOpacity="0">
                        <animate attributeName="fill-opacity" values="0;0.7;0.7;0" dur="7s" begin="-5s" repeatCount="indefinite" />
                      </circle>
                    </g>
                  </svg>

                </div>
              </div>



              {/* Caption Area */}
              <div className="flex flex-col gap-1.5 z-10">
                <p className="text-[11px] font-mono text-[var(--pemali-text-muted)] leading-relaxed">
                  Visualisasi pemindaian otonom dan klasterisasi kerapatan vegetasi hutan di wilayah Ubud dan Denpasar.
                </p>
                <div className="w-full h-px bg-stone-200/60 my-1" />
                <div className="flex justify-between items-center text-[9px] font-mono text-stone-400">
                  <span>SCALE: 1 : 450,000</span>
                  <span>BALI ECO-SYSTEM</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
