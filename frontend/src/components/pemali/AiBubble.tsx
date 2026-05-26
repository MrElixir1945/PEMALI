"use client";

/* Direction: Anthropic Terminal — Warm Editorial */

import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { C } from "@/lib/dashboard";
import { cn } from "@/lib/utils";

interface AiBubbleProps {
  laporanId: number;
}

interface QAResponse {
  question: string;
  answer: string;
  sources: number;
}

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "";

export default function AiBubble({ laporanId }: AiBubbleProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAsk = useCallback(async () => {
    const q = question.trim();
    if (!q || isLoading) return;
    setIsLoading(true);
    setError(null);
    setAnswer(null);

    try {
      const res = await fetch(`${BACKEND}/api/laporan/${laporanId}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: QAResponse = await res.json();
      setAnswer(data.answer);
      setQuestion("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal menghubungi server");
    } finally {
      setIsLoading(false);
    }
  }, [question, isLoading, laporanId]);

  return (
    <>
      {/* Floating button */}
      <motion.button
        className={cn(
          "fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full",
          "bg-[var(--pemali-surface)] border border-[var(--pemali-border)]",
          "text-[var(--pemali-text-primary)] shadow-sm",
          "flex items-center justify-center",
          "hover:bg-[#E8E4DC] transition-colors duration-200",
          isOpen && "opacity-0 pointer-events-none"
        )}
        onClick={() => setIsOpen(true)}
        whileHover={{ scale: 1.04 }}
        whileTap={{ scale: 0.96 }}
        aria-label="Tanya soal laporan ini"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </motion.button>

      {/* Chat panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            className={cn(
              "fixed bottom-6 right-6 z-50 w-[340px]",
              "bg-[var(--pemali-bg)] border border-[var(--pemali-border)]",
              "rounded-lg shadow-xl overflow-hidden flex flex-col"
            )}
            style={{ maxHeight: "420px" }}
            initial={{ opacity: 0, y: 16, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.97 }}
            transition={{ duration: 0.3, ease: [0.0, 0.0, 0.2, 1] }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--pemali-border)]">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-[500] text-[var(--pemali-text-primary)]">
                  Tanya Laporan
                </span>
                <span className="text-[11px] text-[var(--pemali-text-muted)] font-mono">
                  one-shot
                </span>
              </div>
              <button
                onClick={() => {
                  setIsOpen(false);
                  setAnswer(null);
                  setError(null);
                  setQuestion("");
                }}
                className="text-[var(--pemali-text-muted)] hover:text-[var(--pemali-text-primary)] transition-colors"
                aria-label="Tutup"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {/* Answer */}
              {answer && (
                <motion.div
                  className="text-[14px] leading-relaxed text-[var(--pemali-text-primary)]"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.4 }}
                >
                  <div className="text-[11px] text-[var(--pemali-text-muted)] uppercase tracking-wider mb-1 font-mono">
                    Jawaban
                  </div>
                  <div className="prose prose-sm max-w-none" style={{
                    fontFamily: "var(--font-geist-sans)",
                    color: "var(--pemali-text-primary)",
                  }}>
                    {answer}
                  </div>
                </motion.div>
              )}

              {/* Error */}
              {error && (
                <div className="text-[13px] text-[var(--state-error)] bg-[rgba(176,112,104,0.06)] px-3 py-2 rounded">
                  {error}
                </div>
              )}

              {/* Loading */}
              {isLoading && (
                <div className="flex items-center gap-2 text-[var(--pemali-text-muted)] text-[13px]">
                  <span className="inline-block w-2 h-2 rounded-full bg-[var(--pemali-accent)] animate-pulse" />
                  Mencari jawaban...
                </div>
              )}

              {/* Empty state */}
              {!answer && !error && !isLoading && (
                <p className="text-[13px] text-[var(--pemali-text-secondary)] leading-relaxed">
                  Tanyakan apapun tentang laporan ini &mdash; data, tren, atau
                  penjelasan detail. AI akan mencari di konteks laporan ini saja.
                </p>
              )}
            </div>

            {/* Input */}
            <div className="px-4 py-3 border-t border-[var(--pemali-border)]">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAsk()}
                  placeholder={isLoading ? "Mencari..." : "Tanya soal laporan ini..."}
                  disabled={isLoading}
                  className={cn(
                    "flex-1 text-[13px] px-3 py-2 rounded-md",
                    "bg-[var(--pemali-surface)] border border-[var(--pemali-border)]",
                    "text-[var(--pemali-text-primary)] placeholder:text-[var(--pemali-text-muted)]",
                    "outline-none focus:border-[var(--pemali-accent)] transition-colors",
                    "disabled:opacity-50"
                  )}
                  autoFocus
                />
                <button
                  onClick={handleAsk}
                  disabled={isLoading || !question.trim()}
                  className={cn(
                    "px-3 py-2 rounded-md text-[12px] font-[500] transition-colors",
                    "border border-[var(--pemali-border)]",
                    "text-[var(--pemali-text-primary)] hover:bg-[var(--pemali-surface)]",
                    "disabled:opacity-30 disabled:cursor-not-allowed"
                  )}
                >
                  Kirim
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
