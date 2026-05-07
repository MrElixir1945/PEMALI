"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import PemaliMascot from "./PemaliMascot";

const THK_QUOTES = [
  {
    text: "Palemahan — Jaga harmoni dengan alam. Bumi bukan warisan nenek moyang, ia titipan anak cucu.",
    source: "Tri Hita Karana · Palemahan",
  },
  {
    text: "Pawongan — Manusia yang terhubung satu sama lain adalah kekuatan terbesar penjaga lingkungan.",
    source: "Tri Hita Karana · Pawongan",
  },
  {
    text: "Parahyangan — Dalam keselarasan antara manusia dan Tuhan, alam ikut berdoa.",
    source: "Tri Hita Karana · Parahyangan",
  },
  {
    text: "Bumi tidak pernah berbohong. Ia mencatat semua perubahan, dan satelit kini membantu kita membacanya.",
    source: "PEMALI · Prinsip Monitoring",
  },
  {
    text: "Subak bukan sekadar sistem irigasi — ia adalah kearifan lokal yang menjaga keseimbangan ekosistem selama berabad-abad.",
    source: "UNESCO · Warisan Budaya Bali",
  },
  {
    text: "Data satelit adalah mata ketiga yang tidak pernah tidur, menjaga Bali dari ancaman yang tak kasat mata.",
    source: "PEMALI · Filosofi Platform",
  },
];

export default function IdleCanvas() {
  const [quoteIdx, setQuoteIdx] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setQuoteIdx((prev) => (prev + 1) % THK_QUOTES.length);
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  const current = THK_QUOTES[quoteIdx];

  return (
    <div className="w-full h-full flex flex-col items-center justify-center bg-[#FAF9F6] relative overflow-hidden">
      {/* Mascot Area */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="mb-12"
      >
        <div className="p-4">
          <PemaliMascot state="idle" size={140} />
        </div>
      </motion.div>

      {/* Primary Heading */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.8 }}
        className="mb-20 text-center px-4"
      >
        <h2 className="font-serif text-4xl text-stone-900 tracking-tight mb-4">
          Siap Membantu Audit.
        </h2>
        <div className="flex items-center justify-center gap-4">
          <div className="h-[0.5px] w-12 bg-stone-200"></div>
          <p className="text-stone-400 text-[10px] font-sans uppercase tracking-[0.4em] font-bold">
            Environmental Intelligence — Bali
          </p>
          <div className="h-[0.5px] w-12 bg-stone-200"></div>
        </div>
      </motion.div>

      {/* Insight Section */}
      <div className="max-w-md w-full text-center px-8 mb-24 h-24 flex items-center justify-center">
        <AnimatePresence mode="wait">
          <motion.div
            key={quoteIdx}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1 }}
            className="flex flex-col items-center"
          >
            <p className="font-serif text-xl text-stone-600 leading-relaxed italic">
              &ldquo;{current.text}&rdquo;
            </p>
            <span className="text-[10px] font-sans uppercase tracking-[0.2em] text-stone-300 mt-6 font-bold">
              {current.source}
            </span>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Suggestion Grid - 2x2 Grid with 0.5px border */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
        className="grid grid-cols-2 gap-0 max-w-lg border-thin"
      >
        {[
          "Audit kawasan Canggu",
          "Periksa hutan Ubud",
          "Analisis Nusa Penida",
          "Cek lahan Jatiluwih",
        ].map((chip, idx) => (
          <button
            key={chip}
            className={`px-8 py-5 text-[11px] font-sans uppercase tracking-[0.15em] text-stone-500 hover:text-stone-900 transition-all bg-white flex items-center justify-center border-stone-100 ${
              idx % 2 === 0 ? "border-r-[0.5px]" : ""
            } ${idx < 2 ? "border-b-[0.5px]" : ""}`}
          >
            {chip}
          </button>
        ))}
      </motion.div>

      {/* Network Status */}
      <div className="absolute bottom-10 flex items-center gap-3">
        <div className="w-1.5 h-1.5 rounded-full bg-stone-900 animate-pulse" />
        <span className="text-[9px] font-sans uppercase tracking-[0.3em] text-stone-300">
          Agentic Systems Online
        </span>
      </div>
    </div>
  );
}
