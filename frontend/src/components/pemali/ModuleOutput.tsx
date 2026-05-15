"use client";

import { useMemo, useState } from "react";
import { Copy, Check, ChevronDown, ChevronRight } from "lucide-react";

interface ModuleOutputProps {
  data: unknown;
  label?: string;
}

function isTable(data: unknown): data is { headers: string[]; rows: string[][] } {
  if (!data || typeof data !== "object") return false;
  const d = data as Record<string, unknown>;
  return Array.isArray(d.headers) && Array.isArray(d.rows);
}

function isRenderable(data: unknown): data is { render_as: string; data: unknown } {
  if (!data || typeof data !== "object") return false;
  const d = data as Record<string, unknown>;
  return typeof d.render_as === "string" && d.data !== undefined;
}

function JsonView({ data }: { data: unknown }) {
  const [collapsed, setCollapsed] = useState(false);
  const [copied, setCopied] = useState(false);

  const text = useMemo(() => JSON.stringify(data, null, 2), [data]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="relative group">
      <div className="flex items-center justify-between mb-1">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-[10px] font-mono text-[var(--pemali-text-muted)] hover:text-[var(--pemali-text-secondary)] flex items-center gap-1"
        >
          {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          JSON
        </button>
        <button
          onClick={handleCopy}
          className="text-[10px] font-mono text-[var(--pemali-text-muted)] hover:text-[var(--pemali-text-secondary)] flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      {!collapsed && (
        <pre
          className="text-[11px] font-mono leading-relaxed overflow-x-auto rounded-lg p-3"
          style={{
            backgroundColor: "var(--pemali-bg)",
            color: "var(--pemali-text-secondary)",
            border: "1px solid var(--pemali-border)",
          }}
        >
          {highlightJson(text)}
        </pre>
      )}
    </div>
  );
}

function highlightJson(text: string): React.ReactNode {
  const tokens: React.ReactNode[] = [];
  const re = /("(?:\\.|[^"\\])*"|true|false|null|-?\d+\.?\d*|[{}[\],:]|[^\s{}[\]",:]+)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let idx = 0;

  while ((match = re.exec(text)) !== null) {
    if (match.index > lastIndex) {
      tokens.push(<span key={idx++}>{text.slice(lastIndex, match.index)}</span>);
    }
    const val = match[1];
    if (/^"/.test(val)) {
      tokens.push(<span key={idx++} style={{ color: "var(--state-executing)" }}>{val}</span>);
    } else if (/^-?\d+\.?\d*$/.test(val)) {
      tokens.push(<span key={idx++} style={{ color: "var(--state-thinking)" }}>{val}</span>);
    } else if (val === "true" || val === "false") {
      tokens.push(<span key={idx++} style={{ color: "var(--state-spawning)" }}>{val}</span>);
    } else if (val === "null") {
      tokens.push(<span key={idx++} style={{ color: "var(--state-error)" }}>{val}</span>);
    } else {
      tokens.push(<span key={idx++}>{val}</span>);
    }
    lastIndex = match.index + val.length;
  }
  if (lastIndex < text.length) {
    tokens.push(<span key={idx++}>{text.slice(lastIndex)}</span>);
  }
  return tokens;
}

function TableView({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "var(--pemali-border)" }}>
      <table className="w-full text-[11px] font-mono">
        <thead>
          <tr style={{ backgroundColor: "var(--pemali-bg)" }}>
            {headers.map((h, i) => (
              <th
                key={i}
                className="text-left px-3 py-2 text-[var(--pemali-text-muted)] font-medium border-b"
                style={{ borderColor: "var(--pemali-border)" }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr
              key={ri}
              className="hover:brightness-110 transition-colors"
              style={{ borderTop: "1px solid var(--pemali-border)" }}
            >
              {row.map((cell, ci) => (
                <td key={ci} className="px-3 py-2 text-[var(--pemali-text-secondary)]">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ModuleOutput({ data, label }: ModuleOutputProps) {
  const content = useMemo(() => {
    if (!data) return <div className="text-[var(--pemali-text-muted)] text-[12px] italic">No data</div>;

    let parsed = data;
    if (typeof data === "string") {
      try {
        parsed = JSON.parse(data);
      } catch {
        parsed = data;
      }
    }

    if (isRenderable(parsed)) {
      if (parsed.render_as === "table" && isTable(parsed.data)) {
        return <TableView headers={parsed.data.headers} rows={parsed.data.rows} />;
      }
      return <JsonView data={parsed.data} />;
    }

    if (isTable(parsed)) {
      return <TableView headers={parsed.headers} rows={parsed.rows} />;
    }

    return <JsonView data={parsed} />;
  }, [data]);

  return (
    <div className="space-y-2">
      {label && (
        <div className="text-[10px] font-mono text-[var(--pemali-text-muted)] uppercase tracking-widest">
          {label}
        </div>
      )}
      {content}
    </div>
  );
}
