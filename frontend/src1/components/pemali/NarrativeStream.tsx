"use client";

import { useEffect, useRef } from "react";
import { useTelemetryStore } from "@/stores/telemetryStore";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://10.10.20.254:8000";

export default function NarrativeStream() {
  const { addEvent, setConnected } = useTelemetryStore();
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const connect = () => {
      const url = `${BACKEND}/api/telemetry`;
      console.log("[SSE] Connecting to", url);
      const es = new EventSource(url);

      es.onopen = () => {
        console.log("[SSE] Connection opened");
        setConnected(true);
      };

      es.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data);
          addEvent(event);
        } catch (err) {
          console.error("[SSE] Parse error:", err);
        }
      };

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
  }, [addEvent, setConnected]);

  return null;
}
