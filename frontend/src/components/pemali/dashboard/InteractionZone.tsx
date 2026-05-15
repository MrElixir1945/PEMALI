"use client";

import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { motion, AnimatePresence } from "framer-motion";
import type { ChatMessage } from "@/lib/dashboard";

// ── ChatMessages ──
export function ChatMessages({
  messages,
  tokens,
  activeAiBubble,
  progressNote,
}: {
  messages: ChatMessage[];
  tokens: Record<string, string>;
  activeAiBubble?: { phase: string; content: string; isVisible: boolean } | null;
  progressNote?: string;
}) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeAiBubble, progressNote, tokens]);

  return (
    <div className="flex-1 overflow-y-auto px-4 pt-4 pb-2 flex flex-col gap-3">
      {messages.map((m, i) => (
        <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
          <div
            className={`max-w-[85%] px-3.5 py-2.5 text-[13px] leading-relaxed ${
              m.role === "user"
                ? "bg-[var(--pemali-accent)] text-white rounded-[14px_14px_4px_14px]"
                : "bg-[var(--pemali-surface)] text-[var(--pemali-text-primary)] rounded-[14px_14px_14px_4px]"
            }`}
          >
            <ReactMarkdown>{m.content}</ReactMarkdown>
          </div>
        </div>
      ))}

      <AnimatePresence mode="wait">
        {activeAiBubble && (
          <motion.div
            key={activeAiBubble.phase}
            initial={{ opacity: 0, y: 8 }}
            animate={{
              opacity: activeAiBubble.isVisible ? 1 : 0,
              y: activeAiBubble.isVisible ? 0 : 8,
            }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.4, ease: [0.0, 0.0, 0.2, 1] }}
            className="flex justify-start"
          >
            <div className="max-w-[85%] px-3.5 py-2.5 bg-[var(--pemali-surface)] text-[var(--pemali-text-primary)] rounded-[14px_14px_14px_4px] text-[13px] leading-relaxed">
              {activeAiBubble.phase === "loading" ? (
                tokens["manager"] ? (
                  <ReactMarkdown>{tokens["manager"]}</ReactMarkdown>
                ) : (
                  <span className="text-[var(--pemali-text-muted)]">
                    {activeAiBubble.content}
                    <span className="inline-block w-0.5 h-3.5 bg-[var(--pemali-accent)] ml-0.5 align-middle animate-blink-cursor" />
                  </span>
                )
              ) : (
                <ReactMarkdown>{activeAiBubble.content}</ReactMarkdown>
              )}
              {tokens["manager"] && activeAiBubble.phase !== "loading" && (
                <span className="inline-block w-0.5 h-3.5 bg-[var(--pemali-accent)] ml-0.5 align-middle animate-blink-cursor" />
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {progressNote && (
        <div className="flex justify-start">
          <div className="text-[11px] text-[var(--pemali-text-muted)] font-mono px-3.5 py-1">
            {progressNote}
          </div>
        </div>
      )}

      <div ref={endRef} />
    </div>
  );
}

// ── ChatInput ──
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
    <div className="px-4 py-3 border-t border-[var(--pemali-border)] bg-[var(--pemali-bg)]">
      <div className="flex gap-2 bg-[var(--pemali-surface)] border border-[var(--pemali-border)] rounded-xl p-2 items-end">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            e.target.style.height = "auto";
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder={disabled ? "Menunggu respons..." : "Ketik pesan atau instruksi audit..."}
          rows={1}
          className="flex-1 bg-transparent border-none outline-none resize-none text-[13px] text-[var(--pemali-text-primary)] leading-relaxed placeholder:text-[var(--pemali-text-muted)]"
          style={{ fontFamily: "inherit" }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-colors"
          style={{
            background: disabled || !value.trim() ? "var(--pemali-border)" : "var(--pemali-accent)",
            cursor: disabled || !value.trim() ? "default" : "pointer",
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
      <div className="text-[10px] text-[var(--pemali-text-muted)] mt-1 text-center">
        Enter kirim · Shift+Enter baris baru
      </div>
    </div>
  );
}

// ── ModuleOutput ──
export function ModuleOutput({ content }: { content: string }) {
  return (
    <div className="bg-[var(--pemali-surface)] border border-[var(--pemali-border)] rounded-xl p-5 mt-4">
      <div className="text-[11px] font-bold text-[var(--pemali-accent)] uppercase tracking-widest mb-3">
        Laporan Final
      </div>
      <div className="text-[13px] text-[var(--pemali-text-primary)] leading-relaxed pemali-report">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  );
}
