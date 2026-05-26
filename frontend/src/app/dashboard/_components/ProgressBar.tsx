"use client";

import React from "react";
import { C } from "./shared";

export default function ProgressBar({ current, total }: { current: number; total: number }) {
  const pips = Math.min(Math.max(total, 4), 14);
  const filled = Math.round((current / Math.max(total, 1)) * pips);

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8, padding: "7px 14px",
      fontSize: 10, color: C.textMuted,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 2 }}>
        {Array.from({ length: pips }).map((_, i) => {
          const isFilled = i < filled;
          const isActive = i === filled - 1;
          return (
            <React.Fragment key={i}>
              {i > 0 && (
                <div style={{
                  width: 8, height: 1,
                  background: isFilled ? "rgba(128,168,136,0.45)" : "rgba(26,25,20,0.10)",
                }} />
              )}
              <div style={{
                width: 5, height: 5, borderRadius: "50%",
                background: isFilled ? (isActive ? C.accent : C.done) : "rgba(26,25,20,0.13)",
                transition: "background 0.3s ease",
              }} />
            </React.Fragment>
          );
        })}
      </div>
      <span>Step {current} / {total}</span>
    </div>
  );
}
