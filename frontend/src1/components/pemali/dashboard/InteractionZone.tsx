"use client";

import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion, AnimatePresence } from "framer-motion";
import { Sun, CheckCircle, FileText } from "lucide-react";
import type { ChatMessage } from "@/lib/dashboard";

// ── Icons ──
const Icons = {
  Sun: () => <Sun size={20} aria-hidden={true} />,
  CheckCircle: () => <CheckCircle size={20} aria-hidden={true} />,
  FileText: () => <FileText size={18} aria-hidden={true} />,
  Logo: ({ className }: { className?: string }) => (
    <img src="/logo.png" alt="PEMALI" className={className || "w-full h-full object-contain"} />
  )
};

// ── Audit Report Card ──
function AuditReportCard({ onOpen, narrative }: { onOpen: () => void; narrative?: string }) {
  const displayNarrative = narrative && !narrative.startsWith("#")
    ? narrative
    : "Data ekologi telah disintesis. Kami menemukan pola temporal yang membutuhkan perhatian lebih lanjut.";

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full bg-[var(--pemali-surface)] border border-[var(--pemali-border)] rounded-2xl p-6 mt-4 relative overflow-hidden group shadow-lg"
    >
      <div className="absolute top-0 left-0 w-1.5 h-full bg-[var(--pemali-accent)]" />
      <div className="flex flex-col gap-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[var(--pemali-accent)]/10 flex items-center justify-center p-2">
            <Icons.Logo />
          </div>
          <div>
            <h3 className="text-[16px] font-semibold text-[var(--pemali-text-primary)] tracking-tight">Audit Selesai</h3>
            <p className="text-[12px] text-[var(--pemali-text-muted)] font-mono uppercase tracking-wider">Laporan berhasil disusun</p>
          </div>
        </div>

        <p className="text-[14px] text-[var(--pemali-text-secondary)] leading-relaxed">
          &ldquo;{displayNarrative}&rdquo;
        </p>

        <button
          onClick={onOpen}
          className="w-full py-3 bg-[var(--pemali-text-primary)] hover:bg-[var(--pemali-text-primary)]/90 text-[var(--pemali-bg)] rounded-xl text-[13px] font-semibold transition-all flex items-center justify-center gap-2"
        >
          <Icons.FileText />
          Tinjau Laporan Mendalam
        </button>
      </div>
    </motion.div>
  );
}

// ── Chat Messages ──
export function ChatMessages({
  messages,
  onOpenReport,
}: {
  messages: ChatMessage[];
  onOpenReport?: () => void;
}) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col gap-8 w-full">
      {messages.map((m, i) => {
        const isReport = m.role === "assistant" && (m.content.startsWith("# Laporan") || m.content.startsWith("# ") || m.content.includes("Audit Selesai"));

        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
            className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}
          >
            {/* Role Label */}
            <span className="text-[10px] font-bold text-[var(--pemali-text-muted)] uppercase tracking-widest mb-2 px-1">
              {m.role === "user" ? "Penanya" : "Auditor"}
            </span>

            {isReport ? (
              <div className="w-full">
                <AuditReportCard onOpen={onOpenReport || (() => {})} narrative={m.content} />
              </div>
            ) : (
              <div
                className={`max-w-[95%] md:max-w-[85%] px-5 py-4 text-[15px] leading-relaxed tracking-tight ${
                  m.role === "user"
                    ? "bg-[var(--pemali-surface)] border border-[var(--pemali-border)] text-[var(--pemali-text-primary)] rounded-2xl rounded-tr-sm shadow-sm"
                    : "text-[var(--pemali-text-primary)] prose prose-p:text-[var(--pemali-text-primary)] prose-p:leading-relaxed"
                }`}
                style={{ fontFamily: m.role === "assistant" ? "'Lora', serif" : "inherit" }}
              >
                <div className={m.role === "assistant" ? "prose max-w-none" : ""}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                </div>
              </div>
            )}
          </motion.div>
        );
      })}
      <div ref={endRef} />
    </div>
  );
}

export function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (msg: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const v = value.trim();
    if (!v || disabled) return;
    onSend(v);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  return (
    <div className="w-full">
      <div className="flex flex-col bg-[var(--pemali-surface)] border border-[var(--pemali-border)] rounded-2xl p-4 focus-within:border-[var(--pemali-border-glow)] transition-all duration-300 shadow-xl">
        <textarea
          ref={textareaRef}
          value={value}
          disabled={disabled}
          onChange={(e) => {
            if (disabled) return;
            setValue(e.target.value);
            e.target.style.height = "auto";
            e.target.style.height = Math.min(e.target.scrollHeight, 180) + "px";
          }}
          onKeyDown={(e) => {
            if (disabled) return;
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder={disabled ? "PEMALI sedang memproses data..." : "Ketik instruksi audit atau pertanyaan..."}
          rows={1}
          className="w-full bg-transparent border-none outline-none resize-none text-[15px] text-[var(--pemali-text-primary)] leading-relaxed placeholder:text-[var(--pemali-text-muted)] disabled:opacity-50 min-h-[44px]"
          style={{ fontFamily: "inherit" }}
        />
        <div className="flex justify-between items-center mt-3 pt-3 border-t border-[var(--pemali-border)]/50">
          <div className="flex gap-4">
            <span className="text-[10px] text-[var(--pemali-text-muted)] font-mono uppercase tracking-widest">Mode Editor</span>
          </div>
          <button
            onClick={handleSend}
            disabled={disabled || !value.trim()}
            className="px-5 py-1.5 bg-[var(--pemali-accent)] hover:bg-[var(--pemali-accent)]/90 text-white rounded-lg text-[12px] font-semibold transition-all shadow-lg disabled:opacity-30"
          >
            Kirim
          </button>
        </div>
      </div>
    </div>
  );
}
