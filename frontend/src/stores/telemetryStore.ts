"use client";

import { create } from "zustand";

export interface TelemetryEvent {
  trace_id: string;
  node_id: string;
  node_type: "Manager" | "SubAgent" | "Module";
  state: "IDLE" | "THINKING" | "SPAWNING" | "EXECUTING" | "ERROR" | "DONE";
  narrative: string;
  timestamp: number;
  metadata?: {
    tool_name?: string;
    duration_ms?: number;
    rag_sources?: string[];
    phase?: string;
    status?: number;
    error?: string;
  };
}

interface TelemetryStore {
  events: TelemetryEvent[];
  isConnected: boolean;
  activeTraceId: string | null;
  addEvent: (event: TelemetryEvent) => void;
  addEvents: (events: TelemetryEvent[]) => void;
  clearEvents: () => void;
  setConnected: (status: boolean) => void;
  setActiveTraceId: (id: string | null) => void;
}

const MAX_EVENTS = 200;

export const useTelemetryStore = create<TelemetryStore>((set) => ({
  events: [],
  isConnected: false,
  activeTraceId: null,

  addEvent: (event) =>
    set((state) => {
      const trimmed = state.events.length >= MAX_EVENTS
        ? state.events.slice(-(MAX_EVENTS - 1))
        : state.events;
      return { events: [...trimmed, event] };
    }),

  addEvents: (events) =>
    set((state) => {
      const combined = [...state.events, ...events];
      const trimmed = combined.length > MAX_EVENTS
        ? combined.slice(combined.length - MAX_EVENTS)
        : combined;
      return { events: trimmed };
    }),

  clearEvents: () => set({ events: [] }),
  setConnected: (status) => set({ isConnected: status }),
  setActiveTraceId: (id) => set({ activeTraceId: id }),
}));
