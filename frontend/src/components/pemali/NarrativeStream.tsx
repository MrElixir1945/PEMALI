"use client";

import { useEffect, useRef } from "react";
import { useTelemetryStore } from "@/stores/telemetryStore";

export default function NarrativeStream() {
  const { addEvent, setConnected } = useTelemetryStore();
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const connect = () => {
      console.log("[SSE] Connecting to /api/telemetry...");
      const es = new EventSource("/api/telemetry");

      es.onopen = () => {
        console.log("[SSE] Connection opened");
        setConnected(true);
      };

      es.onmessage = (e) => {
        console.log("[SSE] Message received:", e.data);
        try {
          const event = JSON.parse(e.data);
          console.log("[SSE] Parsed event:", event);
          addEvent(event);
        } catch (err) {
          console.error("[SSE] Parse error:", err, "Raw data:", e.data);
        }
      };

      es.onerror = () => {
        console.error("[SSE] Connection error");
        setConnected(false);
        es.close();
        setTimeout(connect, 3000);
      };

      esRef.current = es;
    };

    connect();

    return () => {
      if (esRef.current) {
        console.log("[SSE] Closing connection");
        esRef.current.close();
      }
    };
  }, [addEvent, setConnected]);

  return null;
}
