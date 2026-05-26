"use client";

/* Direction: Dark Terminal Observatory — Scan Metrics Row */

import { motion } from "framer-motion";

interface MetricTile {
  label: string;
  value: string;
  sub: string;
  status: "good" | "warn" | "alert" | "neutral";
}

interface ScanMetricsRowProps {
  summary: Record<string, unknown> | null;
}

function tileColor(status: string) {
  switch (status) {
    case "good":   return "var(--state-complete)";
    case "warn":   return "var(--state-thinking)";
    case "alert":  return "var(--state-error)";
    default:       return "var(--pemali-text-muted)";
  }
}

function buildTiles(summary: Record<string, unknown> | null): MetricTile[] {
  if (!summary) return [];
  const tiles: MetricTile[] = [];

  const w = summary.weather as Record<string, unknown> | undefined;
  if (w?.avg_temp != null) {
    const avg = w.avg_temp as number;
    tiles.push({
      label: "Temp",
      value: `${Math.round(avg)}°C`,
      sub: `max ${Math.round((w.max_temp as number) || avg)}°`,
      status: avg > 33 ? "alert" : avg > 30 ? "warn" : "good",
    });
  }

  const f = summary.fire_hotspots as Record<string, unknown> | undefined;
  if (f?.count != null) {
    const c = f.count as number;
    tiles.push({
      label: "Fire",
      value: `${c}`,
      sub: f.status === "WASPADA" ? "active" : "clear",
      status: c > 0 ? (c > 5 ? "alert" : "warn") : "good",
    });
  }

  const e = summary.earthquakes as Record<string, unknown> | undefined;
  if (e?.count_24h != null) {
    const c = e.count_24h as number;
    tiles.push({
      label: "Seismic",
      value: `${c}`,
      sub: c > 0 ? `max ${(e.max_mag as number)?.toFixed(1)}M` : "none",
      status: c > 0 ? "warn" : "good",
    });
  }

  const a = summary.air_quality as Record<string, unknown> | undefined;
  if (a?.worst_aqi != null) {
    const aqi = a.worst_aqi as number;
    tiles.push({
      label: "AQI",
      value: `${aqi}`,
      sub: (a.worst_location as string) || "",
      status: aqi > 3 ? "alert" : aqi > 2 ? "warn" : "good",
    });
  }

  const o = summary.osint_trends as Record<string, unknown> | undefined;
  if (o) {
    const sentiment = (o.sentiment as string) || "unknown";
    const urgency = (o.urgency as string) || "";
    tiles.push({
      label: "OSINT",
      value: sentiment === "negatif" ? "neg" : sentiment === "positif" ? "pos" : "net",
      sub: urgency,
      status: sentiment === "negatif" ? (urgency === "high" ? "alert" : "warn") : "good",
    });
  }

  return tiles;
}

export default function ScanMetricsRow({ summary }: ScanMetricsRowProps) {
  const tiles = buildTiles(summary);
  if (tiles.length === 0) return null;

  return (
    <div className="flex gap-2 flex-wrap">
      {tiles.map((t, i) => (
        <motion.div
          key={t.label}
          className="flex-1 min-w-[90px] px-3 py-2.5 rounded-lg border text-center"
          style={{
            backgroundColor: `${tileColor(t.status)}08`,
            borderColor: `${tileColor(t.status)}20`,
          }}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: i * 0.04, ease: [0.0, 0.0, 0.2, 1] }}
        >
          <div className="text-[10px] font-mono font-[500] uppercase tracking-wider text-[var(--pemali-text-muted)] mb-0.5">
            {t.label}
          </div>
          <div
            className="text-[18px] font-[500] font-sans leading-tight tabular-nums"
            style={{ color: tileColor(t.status) }}
          >
            {t.value}
          </div>
          <div className="text-[10px] font-mono text-[var(--pemali-text-muted)] truncate mt-0.5">
            {t.sub}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
