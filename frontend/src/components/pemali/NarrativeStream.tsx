"use client";

import { useEffect, useRef, useCallback } from "react";
import { useTelemetryStore } from "@/stores/telemetryStore";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://10.10.20.254:8000";

export default function NarrativeStream() {
  const addEvent = useTelemetryStore((s) => s.addEvent);
  const setConnected = useTelemetryStore((s) => s.setConnected);
  const applyThinkingChunk = useTelemetryStore((s) => s.applyThinkingChunk);
  const setAgentDone = useTelemetryStore((s) => s.setAgentDone);
  const esRef = useRef<EventSource | null>(null);

  const handleMessage = useCallback(
    (e: MessageEvent) => {
      try {
        const event = JSON.parse(e.data);

        // Route agent_thinking events to separate buffer (not main events[])
        if (event.type === "agent_thinking") {
          applyThinkingChunk(event);
          return;
        }

        // Detect SubAgent/Module DONE/ERROR → mark thinking stream as done
        if (
          event.node_id &&
          event.node_type !== "Manager" &&
          (event.state === "DONE" || event.state === "ERROR")
        ) {
          setAgentDone(event.node_id);
        }

        addEvent(event);
      } catch (err) {
        console.error("[SSE] Parse error:", err);
      }
    },
    [addEvent, applyThinkingChunk, setAgentDone]
  );

  useEffect(() => {
    const connect = () => {
      const url = `${BACKEND}/api/telemetry`;
      console.log("[SSE] Connecting to", url);
      const es = new EventSource(url);

      es.onopen = () => {
        console.log("[SSE] Connection opened");
        setConnected(true);
      };

      es.onmessage = handleMessage;

      es.onerror = () => {
        console.warn("[SSE] Connection error — retrying in 3s");
        setConnected(false);
        es.close();
        setTimeout(connect, 3000);
      };

      esRef.current = es;
    };

    connect();

    return () => {
      if (esRef.current) esRef.current.close();
    };
  }, [handleMessage, setConnected]);

  return null;
}
