"use client";

import { useState } from "react";
import { C } from "./shared";

export default function ChatInput({
  onSubmit,
  disabled,
}: {
  onSubmit: (v: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  };

  return (
    <div style={{
      padding: "10px 12px", background: C.surface,
      borderTop: `0.5px solid ${C.border}`,
      display: "flex", flexDirection: "column", gap: 5, flexShrink: 0,
    }}>
      <div style={{
        display: "flex", alignItems: "flex-end", gap: 8, background: C.white,
        border: `0.5px solid ${disabled ? C.border : "rgba(26,25,20,0.22)"}`,
        borderRadius: 8, padding: "7px 10px",
      }}>
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          disabled={disabled}
          placeholder={disabled ? "Streaming aktif..." : "Audit lingkungan [lokasi]..."}
          rows={1}
          style={{
            flex: 1, background: "transparent", border: "none", outline: "none",
            fontSize: 11, lineHeight: 1.5,
            color: disabled ? C.textMuted : C.text,
            fontFamily: "inherit", resize: "none", letterSpacing: "0.02em",
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={disabled || !value.trim()}
          style={{
            width: 22, height: 22, borderRadius: 5,
            background: disabled || !value.trim() ? "rgba(26,25,20,0.08)" : C.text,
            border: "none",
            color: disabled || !value.trim() ? C.textMuted : C.bg,
            cursor: disabled || !value.trim() ? "not-allowed" : "pointer",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 11, flexShrink: 0, transition: "background 0.15s",
          }}
        >
          /
        </button>
      </div>
      {disabled && (
        <div style={{
          fontSize: 9, color: C.textMuted, textAlign: "center", letterSpacing: "0.04em",
        }}>
          streaming aktif &middot; input dinonaktifkan
        </div>
      )}
    </div>
  );
}
