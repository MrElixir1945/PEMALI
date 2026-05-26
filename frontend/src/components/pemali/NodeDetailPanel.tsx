"use client";

import { X, Clock, Wrench } from "lucide-react";
import type { AgentNodeData } from "./AgentNode";

export default function NodeDetailPanel({
  node,
  onClose,
}: {
  node: AgentNodeData;
  onClose: () => void;
}) {
  return (
    <div
      className="border-t"
      style={{
        borderColor: "var(--pemali-border)",
        backgroundColor: "var(--pemali-surface)",
        maxHeight: "35%",
      }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: "var(--pemali-border)" }}>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-semibold text-[var(--pemali-text-primary)]">
            {node.label}
          </span>
          <span className="text-[9px] font-mono text-[var(--pemali-text-muted)]">
            {node.nodeType}
          </span>
        </div>
        <button onClick={onClose} className="text-[var(--pemali-text-muted)] hover:text-[var(--pemali-text-primary)] transition-colors">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="p-4 overflow-y-auto space-y-4">
        <div>
          <div className="text-[9px] font-mono uppercase tracking-widest text-[var(--pemali-text-muted)] mb-2">
            Narrative
          </div>
          <p className="text-sm text-[var(--pemali-text-secondary)] leading-relaxed">
            {node.narrative || "No narrative available."}
          </p>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div
            className="p-3 rounded-lg border"
            style={{ borderColor: "var(--pemali-border)", backgroundColor: "var(--pemali-bg)" }}
          >
            <div className="text-[9px] font-mono uppercase tracking-widest text-[var(--pemali-text-muted)] mb-1">
              State
            </div>
            <div className="text-xs font-mono font-semibold text-[var(--pemali-text-primary)]">
              {node.state}
            </div>
          </div>

          <div
            className="p-3 rounded-lg border"
            style={{ borderColor: "var(--pemali-border)", backgroundColor: "var(--pemali-bg)" }}
          >
            <div className="text-[9px] font-mono uppercase tracking-widest text-[var(--pemali-text-muted)] mb-1">
              Type
            </div>
            <div className="text-xs font-mono font-semibold text-[var(--pemali-text-primary)]">
              {node.nodeType}
            </div>
          </div>

          <div
            className="p-3 rounded-lg border"
            style={{ borderColor: "var(--pemali-border)", backgroundColor: "var(--pemali-bg)" }}
          >
            <div className="text-[9px] font-mono uppercase tracking-widest text-[var(--pemali-text-muted)] mb-1">
              Node ID
            </div>
            <div className="text-xs font-mono font-semibold text-[var(--pemali-text-primary)] truncate">
              {node.id}
            </div>
          </div>
        </div>

        {node.metadata && Object.keys(node.metadata).length > 0 && (
          <div>
            <div className="text-[9px] font-mono uppercase tracking-widest text-[var(--pemali-text-muted)] mb-2">
              Metadata
            </div>
            <div
              className="p-3 rounded-lg border font-mono text-xs text-[var(--pemali-text-secondary)] space-y-1"
              style={{ borderColor: "var(--pemali-border)", backgroundColor: "var(--pemali-bg)" }}
            >
              {node.metadata.tool_name && (
                <div className="flex items-center gap-2">
                  <Wrench className="w-3 h-3 text-[var(--pemali-text-muted)]" />
                  <span>tool: {node.metadata.tool_name}</span>
                </div>
              )}
              {node.metadata.duration_ms !== undefined && (
                <div className="flex items-center gap-2">
                  <Clock className="w-3 h-3 text-[var(--pemali-text-muted)]" />
                  <span>duration: {node.metadata.duration_ms}ms</span>
                </div>
              )}
              {node.metadata.status && (
                <div>status: {node.metadata.status}</div>
              )}
              {node.metadata.error && (
                <div className="text-[var(--state-error)]">error: {node.metadata.error}</div>
              )}
              {node.metadata.phase && (
                <div>phase: {node.metadata.phase}</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
