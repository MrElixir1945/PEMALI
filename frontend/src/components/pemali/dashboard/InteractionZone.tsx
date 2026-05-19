"use client";

import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion, AnimatePresence } from "framer-motion";
import { Sun, CheckCircle, FileText, MessageSquare, Search as SearchIcon } from "lucide-react";
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

  // Filter out internal / non-human-readable assistant messages
  function shouldHide(m: ChatMessage): boolean {
    if (m.role !== "assistant") return false;
    const c = m.content.trim();
    // Manager narrative heading
    if (c.startsWith("**Narasi") || c.startsWith("Narasi Analisis")) return true;
    // Raw JSON plan
    if (c.startsWith("{") || c.includes('"tasks":') || c.includes('"task_id":')) return true;
    // Tool call artifact
    if (c.includes("create_audit_plan")) return true;
    // Very short technical fragments
    if (c.length < 5) return true;
    return false;
  }

  return (
    <div className="flex flex-col gap-8 w-full">
      {messages.filter(m => !shouldHide(m)).map((m, i) => {
        const isReport = m.role === "assistant" && (m.content.startsWith("# Laporan") || m.content.startsWith("# ") || m.content.includes("Audit Selesai"));

        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
            className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}
          >


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
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  return (
    <div className="w-full">
      <div 
        className="w-full flex items-end gap-3 bg-[#e8e4dd] rounded-[9999px] px-5 py-[14px] shadow-[0_1px_4px_rgba(0,0,0,0.08)] focus-within:ring-1 focus-within:ring-[var(--pemali-accent)]/30 transition-all duration-300"
        title="Enter kirim · Shift+Enter baris baru"
      >
        <textarea
          ref={textareaRef}
          value={value}
          disabled={disabled}
          onChange={(e) => {
            if (disabled) return;
            setValue(e.target.value);
            e.target.style.height = "auto";
            e.target.style.height = `${Math.min(e.target.scrollHeight, 180)}px`;
          }}
          onKeyDown={(e) => {
            if (disabled) return;
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder={disabled ? "PEMALI sedang memproses data..." : "Apa yang bisa saya bantu hari ini?"}
          className="flex-1 bg-transparent text-[var(--pemali-text-primary)] placeholder-[var(--pemali-text-muted)] text-[14px] resize-none outline-none leading-relaxed max-h-[180px] overflow-y-auto pt-0.5 disabled:opacity-50"
          rows={1}
          style={{ minHeight: '24px', fontFamily: "inherit" }}
        />

        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className="w-7 h-7 mb-0.5 shrink-0 rounded-full bg-[var(--pemali-accent)] flex items-center justify-center disabled:opacity-30 hover:opacity-90 transition-opacity"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5"><path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"/></svg>
        </button>
      </div>
    </div>
  );
}
