"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { SessionEntry } from "./shared";
import { C } from "./shared";

export default function Sidebar({
  open,
  sessions,
  activeSession,
  onNewSession,
  onSelectSession,
}: {
  open: boolean;
  sessions: SessionEntry[];
  activeSession: string | null;
  onNewSession: () => void;
  onSelectSession: (id: string) => void;
}) {
  const [hovered, setHovered] = useState<string | null>(null);
  const router = useRouter();

  return (
    <div style={{
      width: open ? 200 : 52,
      transition: "width 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
      background: C.surface,
      borderRight: `0.5px solid ${C.border}`,
      flexShrink: 0,
      overflow: "hidden",
      display: "flex",
      flexDirection: "column",
    }}>
      {/* Header */}
      <div style={{
        height: 48,
        display: "flex",
        alignItems: "center",
        padding: open ? "0 16px" : "0 0 0 18px",
        borderBottom: `0.5px solid ${C.borderLight}`,
        flexShrink: 0,
      }}>
        {open ? (
          <span style={{
            fontFamily: "var(--font-lora), Georgia, serif",
            fontSize: 15,
            fontWeight: 500,
            color: C.text,
            letterSpacing: "0.02em",
          }}>
            PEMALI
          </span>
        ) : (
          <span style={{
            fontFamily: "var(--font-lora), Georgia, serif",
            fontSize: 14,
            fontWeight: 500,
            color: C.text,
          }}>
            P
          </span>
        )}
      </div>

      {/* Sessions */}
      <div style={{ flex: 1, padding: "12px 0", overflowY: "auto", overflowX: "hidden" }}>
        {open && (
          <div style={{
            fontSize: 9,
            letterSpacing: "0.12em",
            color: C.textMuted,
            padding: "0 16px 10px",
            textTransform: "uppercase",
            fontWeight: 500,
          }}>
            Sessions
          </div>
        )}
        {sessions.map((s) => {
          const isActive = activeSession === s.id;
          const isHovered = hovered === s.id;
          return (
            <button
              key={s.id}
              onClick={() => onSelectSession(s.id)}
              onMouseEnter={() => setHovered(s.id)}
              onMouseLeave={() => setHovered(null)}
              title={s.label}
              style={{
                width: "100%",
                textAlign: "left",
                padding: open ? "7px 14px" : "7px 0",
                display: "flex",
                alignItems: "center",
                justifyContent: open ? "flex-start" : "center",
                gap: open ? 10 : 0,
                background: isActive ? C.accentBg : isHovered ? "rgba(26,25,20,0.03)" : "transparent",
                border: "none",
                borderLeft: isActive ? `2px solid ${C.accent}` : "2px solid transparent",
                cursor: "pointer",
                transition: "all 0.15s ease",
                position: "relative",
              }}
            >
              <span style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: isActive ? C.accent : "rgba(26,25,20,0.15)",
                flexShrink: 0,
                transition: "background 0.15s",
              }} />
              {open && (
                <div style={{ minWidth: 0, overflow: "hidden" }}>
                  <div style={{
                    fontSize: 11,
                    color: isActive ? C.text : C.textSec,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    fontWeight: isActive ? 500 : 400,
                    transition: "color 0.15s",
                  }}>
                    {s.label}
                  </div>
                  <div style={{
                    fontSize: 9,
                    color: C.textMuted,
                    whiteSpace: "nowrap",
                  }}>
                    {new Date(s.timestamp).toLocaleTimeString("id-ID", {
                      hour: "2-digit",
                      minute: "2-digit",
                      timeZone: "Asia/Makassar",
                    })}
                  </div>
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Nav links */}
      <div style={{
        borderTop: `0.5px solid ${C.borderLight}`,
        flexShrink: 0,
      }}>
        {open && (
          <div style={{
            fontSize: 9,
            letterSpacing: "0.12em",
            color: C.textMuted,
            padding: "12px 16px 8px",
            textTransform: "uppercase",
            fontWeight: 500,
          }}>
            Navigasi
          </div>
        )}
        {[
          { id: "laporan", label: "Laporan", path: "/laporan", icon: "☰" },
          { id: "agentic", label: "Autonomous", path: "/agentic", icon: "◇" },
          { id: "dev", label: "Dev", path: "/dev", icon: "⚙" },
        ].map((nav) => (
          <button
            key={nav.id}
            onClick={() => router.push(nav.path)}
            title={nav.label}
            style={{
              width: "100%",
              textAlign: "left" as const,
              padding: open ? "7px 14px" : "7px 0",
              display: "flex",
              alignItems: "center",
              justifyContent: open ? "flex-start" : "center",
              gap: open ? 10 : 0,
              background: "transparent",
              border: "none",
              borderLeft: "2px solid transparent",
              cursor: "pointer",
              transition: "all 0.15s ease",
              fontSize: open ? 11 : 14,
              color: C.textSec,
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.color = C.text;
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(26,25,20,0.03)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.color = C.textSec;
              (e.currentTarget as HTMLButtonElement).style.background = "transparent";
            }}
          >
            <span style={{ fontSize: 12, flexShrink: 0 }}>{nav.icon}</span>
            {open && <span style={{ fontWeight: 400 }}>{nav.label}</span>}
          </button>
        ))}
      </div>

      {/* New audit */}
      <div style={{
        padding: open ? "10px 14px" : "10px 0",
        borderTop: `0.5px solid ${C.borderLight}`,
        flexShrink: 0,
      }}>
        <button
          onClick={onNewSession}
          style={{
            width: "100%",
            padding: open ? "7px 12px" : "7px 0",
            borderRadius: 6,
            background: C.accentBg,
            border: `0.5px solid ${C.accentBorder}`,
            color: C.accent,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: open ? "flex-start" : "center",
            gap: open ? 8 : 0,
            fontSize: open ? 11 : 14,
            fontWeight: 500,
            transition: "all 0.15s",
          }}
        >
          <span>+</span>
          {open && <span>New Audit</span>}
        </button>
      </div>
    </div>
  );
}
