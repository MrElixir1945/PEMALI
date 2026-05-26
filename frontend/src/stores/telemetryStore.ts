"use client";

import { create } from "zustand";
import type { TelemetryEvent } from "@/lib/dashboard";
export type { TelemetryEvent };

export interface AgentThinkingEvent {
  type: "agent_thinking";
  agent_id: string;
  agent_name: string;
  chunk: string;
  phase: "reasoning" | "tool_call" | "synthesis";
  tool_names?: string[];
  trace_id: string;
  timestamp: number;
}

export type AgentPhase = "reasoning" | "tool_call" | "synthesis" | "done";

export interface AgentThinkingState {
  text: string;
  phase: AgentPhase;
  toolNames: string[];
  isActive: boolean;
}

interface TelemetryStore {
  events: TelemetryEvent[];
  tokens: Record<string, string>;
  isConnected: boolean;
  isStreaming: boolean;
  activeTraceId: string | null;
  /** Per-agent thinking buffers (accumulated text from agent_thinking events) */
  thinkingStates: Record<string, AgentThinkingState>;
  addEvent: (e: TelemetryEvent) => void;
  setEvents: (events: TelemetryEvent[]) => void;
  addToken: (nodeId: string, content: string) => void;
  clearTokens: () => void;
  clearEvents: () => void;
  setConnected: (v: boolean) => void;
  setActiveTraceId: (id: string | null) => void;
  setIsStreaming: (v: boolean) => void;
  /** Append chunk to agent's thinking buffer, update phase */
  applyThinkingChunk: (ev: AgentThinkingEvent) => void;
  /** Mark agent thinking as done (cursor stops, text stays) */
  setAgentDone: (agentId: string) => void;
  clearThinkingStates: () => void;
}

const MAX_EVENTS = 200;

export const useTelemetryStore = create<TelemetryStore>((set) => ({
  events: [],
  tokens: {},
  isConnected: false,
  isStreaming: false,
  activeTraceId: null,
  thinkingStates: {},

  addEvent: (e) =>
    set((s) => {
      const events = [...s.events, e];
      if (events.length > MAX_EVENTS) events.shift();
      return { events };
    }),

  setEvents: (events) => set({ events }),

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

  applyThinkingChunk: (ev) =>
    set((s) => {
      const prev = s.thinkingStates[ev.agent_id] || {
        text: "", phase: "reasoning" as AgentPhase,
        toolNames: [], isActive: true,
      };
      const phase =
        ev.phase === "tool_call" ? "tool_call"
        : ev.phase === "synthesis" ? "synthesis"
        : prev.phase === "tool_call" ? "reasoning"
        : prev.phase;
      return {
        thinkingStates: {
          ...s.thinkingStates,
          [ev.agent_id]: {
            text: prev.text + ev.chunk,
            phase,
            toolNames: ev.tool_names || prev.toolNames,
            isActive: true,
          },
        },
      };
    }),

  setAgentDone: (agentId) =>
    set((s) => {
      const prev = s.thinkingStates[agentId];
      if (!prev) return s;
      return {
        thinkingStates: {
          ...s.thinkingStates,
          [agentId]: { ...prev, isActive: false },
        },
      };
    }),

  clearThinkingStates: () => set({ thinkingStates: {} }),
}));
