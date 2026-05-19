"use client";

import { useState, useMemo } from "react";
import { AnimatePresence } from "framer-motion";
import { useTelemetryStore } from "@/stores/telemetryStore";
import NarrativeCard from "@/components/pemali/NarrativeCard";
import type { ChatMessage } from "./shared";
import { C } from "./shared";
import ChatMessages from "./ChatMessages";
import ChatInput from "./ChatInput";

export default function InteractionZone({
  messages,
  onSend,
}: {
  messages: ChatMessage[];
  onSend: (v: string) => void;
}) {
  const [tab, setTab] = useState<"chat" | "timeline">("chat");
  const { events, tokens, isStreaming } = useTelemetryStore();

  const timelineEvents = useMemo(
    () => events
      .filter((e) => e.node_type !== "Module" && e.state !== "IDLE")
      .slice(-60)
      .reverse(),
    [events]
  );

  const streamingContent = tokens["manager"] ?? "";

  return (
    <div className="flex flex-col flex-1 overflow-hidden" style={{
      minWidth: 0,
      background: C.bg,
    }}>
      {/* Tabs */}
      <div style={{
        display: "flex",
        borderBottom: `0.5px solid ${C.border}`,
        background: C.surface,
        flexShrink: 0,
      }}>
        <TabButton active={tab === "chat"} onClick={() => setTab("chat")}>
          Chat
        </TabButton>
        <TabButton active={tab === "timeline"} onClick={() => setTab("timeline")}>
          Timeline
          {timelineEvents.length > 0 && (
            <span style={{ marginLeft: 5, fontSize: 9, color: C.textMuted }}>
              {timelineEvents.length}
            </span>
          )}
        </TabButton>
      </div>

      {tab === "chat" ? (
        <ChatMessages
          messages={messages}
          streamingContent={streamingContent}
          isStreaming={isStreaming}
        />
      ) : (
        <div style={{ flex: 1, overflowY: "auto", padding: "12px 14px" }}>
          {timelineEvents.length === 0 ? (
            <div style={{
              fontSize: 10,
              color: C.textMuted,
              textAlign: "center",
              paddingTop: 24,
            }}>
              No events yet
            </div>
          ) : (
            <AnimatePresence initial={false}>
              {timelineEvents.map((e, i) => (
                <NarrativeCard key={`${e.node_id}-${e.timestamp}-${i}`} event={e} />
              ))}
            </AnimatePresence>
          )}
        </div>
      )}

      <ChatInput onSubmit={onSend} disabled={isStreaming} />
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "8px 18px",
        fontSize: 11,
        letterSpacing: "0.05em",
        color: active ? C.text : C.textMuted,
        cursor: "pointer",
        background: "transparent",
        border: "none",
        borderBottom: active ? `2px solid ${C.accent}` : "2px solid transparent",
        fontFamily: "inherit",
        fontWeight: active ? 500 : 400,
        transition: "color 0.15s, border-color 0.15s",
        display: "flex",
        alignItems: "center",
      }}
    >
      {children}
    </button>
  );
}
