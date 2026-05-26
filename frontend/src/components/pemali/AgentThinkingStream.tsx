"use client";

/* Direction: Anthropic Terminal — Real-time Agent Thinking Stream */

import Image from "next/image";
import { useEffect, useRef, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTelemetryStore, type AgentPhase } from "@/stores/telemetryStore";
import { Brain, Wrench, FileText, CornerDownRight } from "lucide-react";

interface AgentThinkingStreamProps {
  agentId: string;
  agentName: string;
  isActive: boolean;
}

const PHASE_META: Record<AgentPhase, { label: string; icon: React.ElementType; color: string; bg: string }> = {
  reasoning: {
    label: "Reasoning",
    icon: Brain,
    color: "#5B8DEF",
    bg: "rgba(91, 141, 239, 0.1)",
  },
  tool_call: {
    label: "Tool Call",
    icon: Wrench,
    color: "#D4956A",
    bg: "rgba(212, 149, 106, 0.1)",
  },
  synthesis: {
    label: "Synthesis",
    icon: FileText,
    color: "#8B5CF6",
    bg: "rgba(139, 92, 246, 0.1)",
  },
  done: {
    label: "Done",
    icon: FileText,
    color: "#6B6760",
    bg: "rgba(107, 103, 96, 0.1)",
  },
};

export default function AgentThinkingStream({
  agentId,
  agentName,
  isActive,
}: AgentThinkingStreamProps) {
  const state = useTelemetryStore((s) => s.thinkingStates[agentId]);
  const fullText = state?.text || "";
  const phase = state?.phase || "reasoning";
  const toolNames = state?.toolNames || [];

  // Typewriter: track how many characters have been displayed
  const [displayLen, setDisplayLen] = useState(0);
  const displayLenRef = useRef(0);
  const fullTextRef = useRef("");
  fullTextRef.current = fullText;

  // Typewriter tick: 30ms per character when active
  useEffect(() => {
    if (!fullText) {
      setDisplayLen(0);
      displayLenRef.current = 0;
      return;
    }

    if (!isActive) {
      // Agent done: show everything immediately
      setDisplayLen(fullText.length);
      displayLenRef.current = fullText.length;
      return;
    }

    const interval = setInterval(() => {
      const next = displayLenRef.current + 1;
      if (next >= fullTextRef.current.length) {
        setDisplayLen(fullTextRef.current.length);
        displayLenRef.current = fullTextRef.current.length;
        clearInterval(interval);
      } else {
        displayLenRef.current = next;
        setDisplayLen(next);
      }
    }, 30);

    return () => clearInterval(interval);
  }, [fullText, isActive]);

  const displayText = fullText.slice(0, displayLen);
  const isTyping = isActive && displayLen < fullText.length;

  // Phase change detection for badge animation
  const prevPhaseRef = useRef<AgentPhase>(phase);
  const [justChanged, setJustChanged] = useState(false);
  useEffect(() => {
    if (prevPhaseRef.current !== phase) {
      prevPhaseRef.current = phase;
      setJustChanged(true);
      const t = setTimeout(() => setJustChanged(false), 1500);
      return () => clearTimeout(t);
    }
  }, [phase]);

  const meta = PHASE_META[phase] || PHASE_META.reasoning;
  const PhaseIcon = meta.icon;

  if (!fullText && !isActive) return null;

  return (
    <div className="mt-3 pt-3 border-t border-[var(--pemali-border)]/40">
      {/* Phase indicator badge */}
      <AnimatePresence mode="wait">
        <motion.div
          key={phase + (toolNames.join(",") || "")}
          initial={{ opacity: 0, y: -4, height: 0 }}
          animate={{ opacity: 1, y: 0, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.2 }}
          className="flex items-center gap-2 mb-2"
        >
          <div
            className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-medium tracking-wide"
            style={{
              color: meta.color,
              backgroundColor: meta.bg,
              border: `1px solid ${meta.color}25`,
            }}
          >
            <PhaseIcon size={11} strokeWidth={2} />
            <span className="uppercase">
              {phase === "tool_call" && toolNames.length > 0
                ? toolNames.join(", ")
                : meta.label}
            </span>
            {isTyping && phase === "reasoning" && (
              <span className="relative inline-block w-3.5 h-3.5 ml-1">
                <Image
                  src="/images/logo.png"
                  alt=""
                  width={14}
                  height={14}
                  className="object-contain animate-spin-slow opacity-70"
                />
              </span>
            )}
          </div>
          {justChanged && (
            <motion.span
              initial={{ opacity: 1, x: 0 }}
              animate={{ opacity: 0, x: 8 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="text-[9px] font-mono text-[var(--pemali-text-muted)]"
            >
              ●
            </motion.span>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Thinking content — typewriter */}
      <div className="relative">
        {phase === "tool_call" ? (
          <div
            className="text-[12px] font-mono leading-relaxed rounded-lg px-3 py-2"
            style={{
              color: meta.color,
              backgroundColor: meta.bg,
              border: `1px solid ${meta.color}15`,
            }}
          >
            <div className="flex items-center gap-1.5 text-[11px] opacity-80">
              <CornerDownRight size={12} strokeWidth={2} />
              <span>Validating sensor data...</span>
            </div>
          </div>
        ) : displayText ? (
          <div className="relative">
            <div
              className="text-[13px] leading-relaxed whitespace-pre-wrap"
              style={{ color: "var(--pemali-text-secondary)" }}
            >
              <span className="font-serif">{displayText}</span>
              {isTyping && (
                <span
                  className="inline-block w-[2px] h-[16px] ml-0.5 align-text-bottom animate-blink-cursor"
                  style={{ backgroundColor: "var(--pemali-accent)" }}
                />
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-[12px] text-[var(--pemali-text-muted)] font-mono">
            <span className="relative inline-block w-4 h-4">
              <Image
                src="/images/logo.png"
                alt=""
                width={16}
                height={16}
                className="object-contain animate-spin-slow opacity-50"
              />
            </span>
            <span>{agentName} sedang menganalisis...</span>
          </div>
        )}
      </div>
    </div>
  );
}
