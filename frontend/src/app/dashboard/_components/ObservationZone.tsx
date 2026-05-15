"use client";

import { useMemo } from "react";
import dynamic from "next/dynamic";
import ReactMarkdown from "react-markdown";
import type { TelemetryEvent } from "@/stores/telemetryStore";
import { useTelemetryStore } from "@/stores/telemetryStore";
import ModuleOutput from "@/components/pemali/ModuleOutput";
import { C, getSubAgentIds } from "./shared";
import ManagerCompoundCard from "./ManagerCompoundCard";
import SubAgentGrid from "./SubAgentGrid";

const DAGCanvas = dynamic(() => import("@/components/pemali/DAGCanvas"), { ssr: false });

export default function ObservationZone({ events }: { events: TelemetryEvent[] }) {
  const hasManager = useMemo(() => events.some((e) => e.node_id === "manager"), [events]);
  const hasFinalReport = useMemo(
    () => events.some((e) =>
      e.node_id === "manager" && e.state === "DONE" && e.metadata?.type === "final_report"
    ), [events]
  );
  const finalEvent = useMemo(
    () => events.find((e) =>
      e.node_id === "manager" && e.state === "DONE" && e.metadata?.type === "final_report"
    ), [events]
  );
  const tokens = useTelemetryStore((s) => s.tokens);
  const isStreaming = useTelemetryStore((s) => s.isStreaming);
  const synthesisContent = tokens["manager"] ?? "";
  const reportContent = finalEvent?.narrative ?? synthesisContent;
  const moduleEvents = useMemo(() => events.filter((e) => e.node_type === "Module"), [events]);
  const hasSubAgents = useMemo(() => getSubAgentIds(events).length > 0, [events]);
  const isSubstantialReport = reportContent.length > 300;
  const shouldShowReport = isStreaming || (reportContent && (hasSubAgents || isSubstantialReport));

  const cardShadow = "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)";

  return (
    <div style={{
      flex: 1,
      display: "flex",
      flexDirection: "column",
      padding: "16px",
      gap: 12,
      overflowY: "auto",
      minWidth: 0,
    }}>
      {/* Section header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
      }}>
        <span style={{
          fontSize: 9,
          letterSpacing: "0.14em",
          color: C.textMuted,
          textTransform: "uppercase",
          fontWeight: 500,
        }}>
          Observation Zone
        </span>
        <div style={{ flex: 1, height: 1, background: C.borderLight }} />
      </div>

      {/* Empty state */}
      {!hasManager && (
        <div style={{
          background: C.white,
          border: `0.5px dashed ${C.border}`,
          borderRadius: 12,
          padding: "48px 24px",
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 10,
          boxShadow: cardShadow,
        }}>
          <div style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            background: C.accentBg,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 20,
            color: C.accent,
          }}>
            ◈
          </div>
          <div style={{
            fontFamily: "var(--font-lora), Georgia, serif",
            fontSize: 14,
            color: C.text,
            fontWeight: 500,
          }}>
            Belum ada audit berjalan
          </div>
          <div style={{
            fontSize: 11,
            color: C.textMuted,
            lineHeight: 1.6,
            maxWidth: 240,
          }}>
            Kirim prompt di panel kanan untuk memulai audit lingkungan
          </div>
        </div>
      )}

      {hasManager && <ManagerCompoundCard events={events} />}

      {hasManager && (
        <>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}>
            <span style={{
              fontSize: 9,
              letterSpacing: "0.12em",
              color: C.textMuted,
              textTransform: "uppercase",
              fontWeight: 500,
            }}>
              Sub-agents
            </span>
            <div style={{ flex: 1, height: 1, background: C.borderLight }} />
          </div>
          <SubAgentGrid events={events} />
        </>
      )}

      {hasManager && events.length > 2 && (
        <>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}>
            <span style={{
              fontSize: 9,
              letterSpacing: "0.12em",
              color: C.textMuted,
              textTransform: "uppercase",
              fontWeight: 500,
            }}>
              DAG Topology
            </span>
            <div style={{ flex: 1, height: 1, background: C.borderLight }} />
          </div>
          <div className="flex flex-col rounded-xl overflow-hidden flex-shrink-0" style={{
            minHeight: 220,
            maxHeight: 400,
            border: `0.5px solid ${C.border}`,
            background: C.white,
            boxShadow: cardShadow,
          }}>
            <DAGCanvas />
          </div>
        </>
      )}

      {moduleEvents.length > 0 && (
        <>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}>
            <span style={{
              fontSize: 9,
              letterSpacing: "0.12em",
              color: C.textMuted,
              textTransform: "uppercase",
              fontWeight: 500,
            }}>
              Module Outputs
            </span>
            <div style={{ flex: 1, height: 1, background: C.borderLight }} />
          </div>
          {moduleEvents.slice(-4).map((evt) => (
            <ModuleOutput
              key={`${evt.node_id}-${evt.timestamp}`}
              data={evt.metadata ?? evt.narrative}
              label={evt.node_id}
            />
          ))}
        </>
      )}

      {shouldShowReport && (
        <div style={{
          background: C.white,
          border: `0.5px solid ${C.border}`,
          borderRadius: 12,
          overflow: "hidden",
          flexShrink: 0,
          boxShadow: cardShadow,
        }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "10px 16px",
            borderBottom: `0.5px solid ${C.borderLight}`,
            background: "rgba(26,25,20,0.02)",
          }}>
            <span style={{
              fontSize: 10,
              letterSpacing: "0.08em",
              color: C.textSec,
              fontWeight: 500,
              textTransform: "uppercase",
            }}>
              Final Report
            </span>
            {hasFinalReport && (
              <span style={{
                fontSize: 9,
                color: C.done,
                letterSpacing: "0.06em",
                fontWeight: 500,
              }}>
                complete
              </span>
            )}
            {isStreaming && !hasFinalReport && (
              <span style={{
                fontSize: 9,
                color: C.accent,
                letterSpacing: "0.06em",
                fontWeight: 500,
              }}>
                streaming
              </span>
            )}
          </div>
          <div className="pemali-report" style={{
            padding: "14px 16px",
            fontSize: 11,
            lineHeight: 1.75,
            color: C.text,
            maxHeight: 400,
            overflowY: "auto",
          }}>
            <ReactMarkdown>{reportContent}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
