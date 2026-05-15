"use client";

import { create } from "zustand";
import type { TelemetryEvent } from "@/lib/dashboard";
export type { TelemetryEvent };

interface TelemetryStore {
  events: TelemetryEvent[];
  tokens: Record<string, string>;
  isConnected: boolean;
  isStreaming: boolean;
  activeTraceId: string | null;
  addEvent: (e: TelemetryEvent) => void;
  addToken: (nodeId: string, content: string) => void;
  clearTokens: () => void;
  clearEvents: () => void;
  setConnected: (v: boolean) => void;
  setActiveTraceId: (id: string | null) => void;
  setIsStreaming: (v: boolean) => void;
}

const MAX_EVENTS = 200;

export const useTelemetryStore = create<TelemetryStore>((set) => ({
  events: [],
  tokens: {},
  isConnected: false,
  isStreaming: false,
  activeTraceId: null,

  addEvent: (e) =>
    set((s) => {
      const events = [...s.events, e];
      if (events.length > MAX_EVENTS) events.shift();
      return { events };
    }),

  addToken: (nodeId, content) =>
    set((s) => ({
      tokens: {
        ...s.tokens,
        [nodeId]: (s.tokens[nodeId] ?? "") + content,
      },
    })),

  clearTokens: () => set({ tokens: {} }),
  clearEvents: () => set({ events: [] }),
  setConnected: (v) => set({ isConnected: v }),
  setActiveTraceId: (id) => set({ activeTraceId: id }),
  setIsStreaming: (v) => set({ isStreaming: v }),
}));
