"use client";

import { useEffect, useRef } from "react";
import { useTelemetryStore } from "@/stores/telemetryStore";

export default function NarrativeStream() {
  const { addEvent, setConnected } = useTelemetryStore();
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const connect = () => {
      const es = new EventSource("/api/telemetry");

      es.onopen = () => setConnected(true);

      es.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data);
          addEvent(event);
        } catch (err) {
          console.error("SSE parse error:", err);
        }
      };

      es.onerror = () => {
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
  }, [addEvent, setConnected]);

  return null;
}
