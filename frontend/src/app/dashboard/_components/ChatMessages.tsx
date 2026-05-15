"use client";

import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "./shared";
import { C } from "./shared";

export default function ChatMessages({
  messages,
  streamingContent,
  isStreaming,
}: {
  messages: ChatMessage[];
  streamingContent: string;
  isStreaming: boolean;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  return (
    <div style={{
      flex: 1, overflowY: "auto", padding: "12px",
      display: "flex", flexDirection: "column", gap: 8,
    }}>
      {messages.map((m, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          style={{
            display: "flex",
            justifyContent: m.role === "user" ? "flex-end" : "flex-start",
          }}
        >
          <div style={{
            maxWidth: "90%", fontSize: 11, lineHeight: 1.65,
            padding: "8px 11px",
            borderRadius: m.role === "user" ? "8px 8px 2px 8px" : "8px 8px 8px 2px",
            background: m.role === "user" ? C.text : C.white,
            color: m.role === "user" ? C.bg : C.text,
            border: m.role === "user" ? "none" : `0.5px solid ${C.border}`,
            boxShadow: m.role === "user" ? "0 1px 3px rgba(0,0,0,0.08)" : "0 1px 2px rgba(0,0,0,0.03)",
          }}>
            {m.content}
          </div>
        </motion.div>
      ))}

      {isStreaming && streamingContent && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ display: "flex", justifyContent: "flex-start" }}
        >
          <div style={{
            maxWidth: "95%", fontSize: 11, lineHeight: 1.7,
            padding: "9px 12px", borderRadius: "8px 8px 8px 2px",
            background: C.white, border: `0.5px solid ${C.accentBorder}`,
          }}>
            <div style={{
              fontSize: 9, letterSpacing: "0.10em", color: C.synthText, marginBottom: 5,
            }}>
              SYNTHESIS &middot; STREAMING
            </div>
            <div className="pemali-report">
              <ReactMarkdown>{streamingContent}</ReactMarkdown>
            </div>
            <span style={{
              display: "inline-block", width: 6, height: 11,
              background: C.accent, verticalAlign: "bottom",
              borderRadius: 1, marginLeft: 2,
              animation: "blink-cursor 0.9s step-end infinite",
            }} />
          </div>
        </motion.div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
