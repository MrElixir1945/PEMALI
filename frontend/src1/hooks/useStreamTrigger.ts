"use client";

import { useCallback, useRef } from "react";
import { useTelemetryStore } from "@/stores/telemetryStore";

export function useStreamTrigger() {
  const addEvent = useTelemetryStore((s) => s.addEvent);
  const addToken = useTelemetryStore((s) => s.addToken);
  const clearTokens = useTelemetryStore((s) => s.clearTokens);
  const setIsStreaming = useTelemetryStore((s) => s.setIsStreaming);
  const abortRef = useRef<AbortController | null>(null);

  const trigger = useCallback(
    async (prompt: string) => {
      clearTokens();
      abortRef.current = new AbortController();
      setIsStreaming(true);

      try {
        const response = await fetch("/api/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt }),
          signal: abortRef.current.signal,
        });

        if (!response.ok) {
          console.error("[Stream] HTTP error:", response.status);
          setIsStreaming(false);
          return;
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let currentEvent = "";
          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));
                if (currentEvent === "token") {
                  addToken(data.node_id || "agent", data.content);
                } else {
                  addEvent(data);
                }
              } catch {
                // skip unparseable lines
              }
              currentEvent = "";
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== "AbortError") {
          console.error("[Stream] Error:", err);
        }
      } finally {
        setIsStreaming(false);
      }
    },
    [addEvent, addToken, clearTokens, setIsStreaming]
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { trigger, abort };
}
