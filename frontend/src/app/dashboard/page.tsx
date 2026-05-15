"use client";

/**
 * PEMALI Dashboard — Anthropic Terminal
 * Layout: Sidebar | AgentArea + DAG/Report | Chat
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useTelemetryStore } from "@/stores/telemetryStore";
import type { TelemetryEvent, TokenEvent, ChatMessage, Session } from "@/lib/dashboard";
import {
  StatusBar,
  Sidebar,
  AgentArea,
  FinalReport,
} from "@/components/pemali/dashboard/ObservationZone";
import {
  ChatMessages,
  ChatInput,
} from "@/components/pemali/dashboard/InteractionZone";

export default function PemaliDashboard() {
  const {
    events,
    tokens,
    isConnected,
    isStreaming,
    addEvent,
    addToken,
    clearTokens,
    clearEvents,
    setConnected,
    setActiveTraceId,
    setIsStreaming,
  } = useTelemetryStore();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [finalReport, setFinalReport] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const [activeAiBubble, setActiveAiBubble] = useState<{
    phase: "loading" | "planning" | "synthesis" | "chat";
    content: string;
    isVisible: boolean;
  } | null>(null);
  const [progressNote, setProgressNote] = useState("");
  const [lastEventTime, setLastEventTime] = useState<number>(Date.now());

  // Update last event time when new events arrive
  useEffect(() => {
    if (events.length > 0) {
      setLastEventTime(Date.now());
    }
  }, [events]);

  // Safety timeout: reset isStreaming if no events for 3 seconds while streaming
  useEffect(() => {
    if (!isStreaming) return;
    const timer = setTimeout(() => {
      const timeSinceLastEvent = Date.now() - lastEventTime;
      if (timeSinceLastEvent > 3000) {
        setIsStreaming(false);
      }
    }, 3500);
    return () => clearTimeout(timer);
  }, [isStreaming, lastEventTime]);

  // Save completed assistant responses to messages
  const [lastProcessedEventCount, setLastProcessedEventCount] = useState(0);
  useEffect(() => {
    if (events.length <= lastProcessedEventCount) return;
    const newEvents = events.slice(lastProcessedEventCount);
    setLastProcessedEventCount(events.length);

    for (const ev of newEvents) {
      // Chat response complete (Manager DONE without phase/type)
      if (ev.node_id === "manager" && ev.state === "DONE" && !ev.metadata?.phase && !ev.metadata?.type) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: ev.narrative, ts: ev.timestamp },
        ]);
        setActiveAiBubble(null);
      }
      // Audit complete — final report goes to left panel
      if (ev.node_id === "manager" && ev.state === "DONE" && ev.metadata?.type === "final_report") {
        setFinalReport(ev.narrative);
        setIsStreaming(false);
      }
    }
  }, [events, lastProcessedEventCount]);

  // detect planning phase → show bubble
  useEffect(() => {
    const planningEvent = events.find(
      (e) =>
        e.node_id === "manager" &&
        e.state === "THINKING" &&
        e.metadata?.phase === "planning"
    );
    if (planningEvent && (!activeAiBubble || activeAiBubble.phase === "loading")) {
      setActiveAiBubble({
        phase: "planning",
        content: planningEvent.narrative,
        isVisible: true,
      });
    }
  }, [events, activeAiBubble]);

  // detect synthesis phase → fade transition
  useEffect(() => {
    const synthesisEvent = events.find(
      (e) =>
        e.node_id === "manager" &&
        e.state === "THINKING" &&
        e.metadata?.phase === "synthesis"
    );
    if (synthesisEvent && activeAiBubble?.phase === "planning") {
      setActiveAiBubble((prev) =>
        prev ? { ...prev, isVisible: false } : null
      );
      setTimeout(() => {
        setActiveAiBubble({
          phase: "synthesis",
          content: synthesisEvent.narrative,
          isVisible: true,
        });
      }, 400);
    }
  }, [events, activeAiBubble]);

  // detect general chat THINKING (no phase metadata) — bukan DONE
  useEffect(() => {
    const chatEvent = events.find(
      (e) =>
        e.node_id === "manager" &&
        e.state === "THINKING" &&
        !e.metadata?.phase &&
        !e.metadata?.type
    );
    if (chatEvent && (!activeAiBubble || activeAiBubble.phase === "loading")) {
      setActiveAiBubble({
        phase: "chat",
        content: chatEvent.narrative,
        isVisible: true,
      });
    }
  }, [events, activeAiBubble]);

  // progress updates during execute/validate
  useEffect(() => {
    const progressEvent = events.find(
      (e) =>
        e.node_id === "manager" &&
        e.state === "THINKING" &&
        e.metadata?.phase === "execute" &&
        e.metadata?.phase_step === "progress"
    );
    if (progressEvent) {
      const done = progressEvent.metadata?.done as string[] ?? [];
      const pending = progressEvent.metadata?.pending as string[] ?? [];
      setProgressNote(`${done.length}/${done.length + pending.length} agent selesai`);
    }
    const validateEvent = events.find(
      (e) =>
        e.node_id === "manager" &&
        e.state === "THINKING" &&
        e.metadata?.phase === "validate"
    );
    if (validateEvent && !progressEvent) {
      setProgressNote("Memvalidasi data...");
    }
  }, [events]);

  // send message → SSE stream
  const handleSend = useCallback(
    async (text: string) => {
      setMessages((prev) => [
        ...prev,
        { role: "user", content: text, ts: Date.now() },
      ]);
      clearTokens();
      clearEvents();
      setLastProcessedEventCount(0);
      setFinalReport(null);
      setActiveAiBubble({
        phase: "loading",
        content: "Menunggu respons...",
        isVisible: true,
      });
      setProgressNote("");
      setIsStreaming(true);
      setConnected(true);

      const sessionId = `sess-${Date.now()}`;
      setActiveSessionId(sessionId);
      setSessions((prev) => [
        { id: sessionId, label: text.slice(0, 32), ts: Date.now() },
        ...prev.slice(0, 19),
      ]);

      abortRef.current?.abort();

      try {
        const BACKEND =
          process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
        const res = await fetch(`${BACKEND}/api/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: text }),
        });

        if (!res.ok || !res.body) {
          throw new Error(`HTTP ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          let eventType = "";
          let dataLine = "";

          for (const line of lines) {
            if (line.startsWith("event:")) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              dataLine = line.slice(5).trim();
            } else if (line === "" && dataLine) {
              try {
                const parsed = JSON.parse(dataLine);
                if (eventType === "state") {
                  const ev = parsed as TelemetryEvent;
                  addEvent(ev);
                  setActiveTraceId(ev.trace_id);
                } else if (eventType === "token") {
                  const tk = parsed as TokenEvent;
                  addToken(tk.node_id, tk.content);
                }
              } catch {
                // bad json, skip
              }
              eventType = "";
              dataLine = "";
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== "AbortError") {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: `⚠️ Koneksi gagal: ${err.message}`,
              ts: Date.now(),
            },
          ]);
        }
      } finally {
        setIsStreaming(false);
      }
    },
    [
      addEvent,
      addToken,
      clearEvents,
      clearTokens,
      setActiveTraceId,
      setConnected,
      setIsStreaming,
    ]
  );

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-[var(--pemali-bg)] text-[var(--pemali-text-primary)]">
      <StatusBar
        isConnected={isConnected}
        isStreaming={isStreaming}
        eventCount={events.length}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* ── Sidebar ── */}
        <Sidebar
          sessions={sessions}
          onNewAudit={() => {
            clearEvents();
            clearTokens();
            setMessages([]);
            setFinalReport(null);
            setActiveSessionId(null);
          }}
          onSelectSession={(id) => setActiveSessionId(id)}
          activeSessionId={activeSessionId}
        />

        {/* ── Main ── */}
        <div className="flex flex-1 overflow-hidden">
          {/* Observation Zone */}
          <div className="flex-[1.5] flex flex-col border-r border-[var(--pemali-border)] overflow-hidden">
            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
              {/* Agent Status Area */}
              <AgentArea events={events} />

              {/* Final Report — shows during synthesis streaming then stays */}
              {(finalReport || (activeAiBubble?.phase === "synthesis" && tokens["manager"])) && (
                <div className="min-h-0">
                  <FinalReport
                    content={finalReport || tokens["manager"] || ""}
                    isLoading={!finalReport && activeAiBubble?.phase === "synthesis"}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Interaction Zone */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <ChatMessages
              messages={messages}
              tokens={tokens}
              activeAiBubble={activeAiBubble}
              progressNote={progressNote}
            />
            <ChatInput onSend={handleSend} disabled={isStreaming} />
          </div>
        </div>
      </div>
    </div>
  );
}
