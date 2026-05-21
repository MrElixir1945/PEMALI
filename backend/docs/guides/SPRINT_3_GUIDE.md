# PEMALI Sprint 3 — Implementation Guide

> **Status:** PLAN MODE — semua keputusan design sudah disepakati.
> **Goal:** Narrative Prompt Contracts + SDUI + SSE Telemetry untuk frontend transparency.
> **Durasi:** 1-2 minggu / ~23 jam kerja.
> **Bahasa:** Full Indonesia. Gaya: Anthropic (clean, minimal).

---

## 0. Keputusan Design (Sudah Final)

| # | Keputusan | Detail |
|---|-----------|--------|
| 1 | RAG context | Raw text, masuk langsung ke system prompt dengan cara baca eksplisit |
| 2 | State machine | Ditentukan oleh agent sendiri berdasarkan kondisi internal (tidak hard-coded) |
| 3 | Metadata TelemetryEvent | Tambah field `metadata: dict` berisi `tool_name` dan `duration_ms` |
| 4 | Duration tracking | Gunakan `time.monotonic()` sebelum & sesudah tool call |
| 5 | Frontend state | Zustand store (`stores/telemetryStore.ts`), max buffer 200 events |
| 6 | Gaya visual | Anthropic terminal, PEMALI CSS tokens, tanpa emoji berlebihan |

---

## 1. Arsitektur Target

```
User Prompt
    ↓
Manager Agent  ← system prompt dengan NARRATIVE CONTRACT + RAG reading instructions
    ↓ (emit TelemetryEvent ke SSE)
Sub-Agents     ← system prompt dengan NARRATIVE CONTRACT + state machine
    ↓ (track duration via time.monotonic())
Modules         ← return raw data + metadata (tool_name, duration_ms)
    ↓
SSE /api/telemetry → frontend NarrativeStream → Zustand store → semua komponen
```

---

## 2. Backend — Daftar Perubahan

### 2.1 `core/models.py` — Tambah field `metadata` ke `TelemetryEvent`

**File:** `core/models.py` (line 36-45)

**Current state:**
```python
class TelemetryEvent(BaseModel):
    trace_id: str
    node_id: str
    node_type: str
    state: NodeState
    narrative: str
    timestamp: int = Field(default_factory=lambda: int(time.time()))
```

**Target (tambah 1 field):**
```python
class TelemetryEvent(BaseModel):
    trace_id: str
    node_id: str
    node_type: str
    state: NodeState
    narrative: str
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadata opsional: tool_name, duration_ms, rag_sources")
```

**Caranya:** Tambah baris `metadata: Optional[Dict[str, Any]] = Field(default=None, ...)` setelah `timestamp`.

**Update import:** Pastikan `from typing import Optional, Dict, Any` sudah ada di atas file (saat ini sudah ada `from typing import List, Dict, Any, Optional`).

---

### 2.2 `core/orchestrator.py` — Update Manager system prompt

**File:** `core/orchestrator.py` (line 262-265)

**Current state:**
```python
sys_prompt = (
    "You are MANAGER AGENT. Analyze and delegate. "
    "Output JSON matching: {'trace_id': 'string', 'tasks': [{'task_id': 'string', 'target_agent': 'string', 'intent': 'string', 'depends_on': ['task_id']}]}"
)
```

**Target (tambah NARRATIVE CONTRACT + RAG reading instructions):**
```python
sys_prompt = (
    "[PEMALI NARRATIVE CONTRACT v1]\n"
    "Anda adalah MANAGER AGENT dalam sistem audit lingkungan Bali.\n"
    "Tugas Anda: analisis permintaan user, dekomposisi menjadi sub-tugas terstruktur, delegasikan ke Sub-Agent yang sesuai, lalu sintesis hasilnya.\n\n"
    
    "# ATURAN NARASI\n"
    "SEBELUM mengambil keputusan apapun, ceritakan proses berpikir Anda dalam bahasa Indonesia yang natural.\n"
    "Gunakan narasi yang jelas: apa yang Anda amati, mengapa Anda memutuskan demikian, apa langkah selanjutnya.\n"
    "Narasi Anda akan ditampilkan langsung ke pengguna — bukan prompt internal.\n\n"
    
    "# CARA MEMBACA RAG CONTEXT\n"
    "Jika tersedia konteks dari memori historis (RAG context), gunakan dengan cara berikut:\n"
    "1. IDENTIFIKASI: perhatikan lokasi geografis yang disebutkan dalam konteks.\n"
    "2. BANDINGKAN: bandingkan kondisi saat ini dengan catatan historis.\n"
    "3. PRIORITASKAN: jika ada tren memburuk, prioritaskan area tersebut.\n"
    "4. GUNAKAN SEBAGAI BASELINE: jadikan data historis sebagai titik awal analisis.\n"
    "5. JANGAN ULANGI: jika audit sebelumnya sudah selesai untuk area yang sama, gunakan sebagai referensi, bukan ulangi dari awal.\n\n"
    
    "# FORMAT OUTPUT\n"
    "Output WAJIB dalam JSON:\n"
    "{'trace_id': 'string', 'tasks': [{'task_id': 'string', 'target_agent': 'string', 'intent': 'string', 'depends_on': ['task_id']}]}\n\n"
    
    "# KONTEKS HISTORIS\n"
    f"Berikut adalah hasil audit sebelumnya yang relevan:\n{rag_context}\n"
)
```

**Catatan:** Perhatikan bahwa `rag_context` tetap disisipkan di akhir prompt sebagai bagian dari system prompt yang sama. Jangan pisahkan ke message terpisah.

---

### 2.3 `core/orchestrator.py` — Update SubAgent system prompt

**File:** `core/orchestrator.py` (line 103)

**Current state:**
```python
messages = [{"role": "system", "content": f"You are {self.task.target_agent}. Task: {self.task.intent}. Shared data is in parameters if available. If tool execution fails, read the error message and fix your parameters."}]
```

**Target (tambah NARRATIVE CONTRACT + state machine):**
```python
system_prompt = (
    "[PEMALI NARRATIVE CONTRACT v1]\n"
    f"Anda adalah {self.task.target_agent}, spesialis dalam audit lingkungan Bali.\n"
    f"Tugas spesifik Anda: {self.task.intent}\n\n"
    
    "# ATURAN STATE MACHINE\n"
    "Anda bertanggung jawab menentukan state Anda sendiri berdasarkan kondisi internal:\n"
    "- THINKING: saat Anda menganalisis instruksi dan mempertimbangkan tools yang tersedia.\n"
    "- EXECUTING: saat Anda menjalankan tool dan menunggu hasilnya.\n"
    "- DONE: saat semua data terkumpul dan tugas selesai.\n"
    "- ERROR: saat terjadi kegagalan yang tidak bisa dipulihkan.\n\n"
    
    "# ATURAN NARASI\n"
    "SEBELUM memilih tools: ceritakan tools mana yang Anda pertimbangkan dan mengapa.\n"
    "SEBELUM eksekusi tools: sebutkan [tool_name] yang akan digunakan dan tujuannya.\n"
    "SAAT error terjadi: jelaskan masalahnya dan strategi koreksi yang Anda coba.\n"
    "SAAT selesai: ringkas apa yang telah Anda lakukan dan temuan utama.\n"
    "Semua narasi dalam bahasa Indonesia natural.\n\n"
    
    "# ATURAN KOREKSI DIRI\n"
    "Jika tool gagal (status 4xx/5xx), baca pesan error, sesuaikan parameter, dan coba lagi.\n"
    "Maksimal 3x percobaan per tool.\n\n"
    
    "# ATURAN TEKNIS\n"
    f"Gunakan function-calling JSON standard. Shared data tersedia di parameters jika ada."
)

messages = [{"role": "system", "content": system_prompt}]
```

---

### 2.4 `core/orchestrator.py` — Tambah duration tracking di `_execute_tool()`

**File:** `core/orchestrator.py` (line 229-238)

**Current state:**
```python
async def _execute_tool(self, name: str, args: Dict, tool_call_id: str) -> Dict:
    await telemetry.emit(TelemetryEvent(
        trace_id=self.trace_id, node_id=name, node_type="Module",
        state=NodeState.EXECUTING, narrative=f"Eksekusi internal modul {name}..."
    ))
    try:
        output = await registry.execute_tool(name, args, session_id=self.session_id)
        return {"tool_call_id": tool_call_id, "tool_name": name, "output": output.model_dump()}
    except Exception as e:
        return {"tool_call_id": tool_call_id, "tool_name": name, "output": {"status": 500, "error_msg": str(e)}}
```

**Target (tambah `time.monotonic()` dan metadata):**
```python
import time  # pastikan ini sudah ada di atas file (saat ini belum ada di import list orchestrator)

async def _execute_tool(self, name: str, args: Dict, tool_call_id: str) -> Dict:
    start_time = time.monotonic()
    
    await telemetry.emit(TelemetryEvent(
        trace_id=self.trace_id, node_id=name, node_type="Module",
        state=NodeState.EXECUTING, narrative=f"Menjalankan modul [{name}]...",
        metadata={"tool_name": name, "phase": "start"}
    ))
    try:
        output = await registry.execute_tool(name, args, session_id=self.session_id)
        duration_ms = round((time.monotonic() - start_time) * 1000, 2)
        
        await telemetry.emit(TelemetryEvent(
            trace_id=self.trace_id, node_id=name, node_type="Module",
            state=NodeState.DONE, narrative=f"Modul [{name}] selesai.",
            metadata={"tool_name": name, "duration_ms": duration_ms, "status": output.status}
        ))
        
        return {"tool_call_id": tool_call_id, "tool_name": name, "output": output.model_dump()}
    except Exception as e:
        duration_ms = round((time.monotonic() - start_time) * 1000, 2)
        
        await telemetry.emit(TelemetryEvent(
            trace_id=self.trace_id, node_id=name, node_type="Module",
            state=NodeState.ERROR, narrative=f"Modul [{name}] gagal: {str(e)[:200]}",
            metadata={"tool_name": name, "duration_ms": duration_ms, "error": str(e)[:200]}
        ))
        
        return {"tool_call_id": tool_call_id, "tool_name": name, "output": {"status": 500, "error_msg": str(e)}}
```

**Checklist tambahan pada `_execute_tool`:**
- Pastikan `import time` ada di bagian atas `orchestrator.py` (saat ini belum ada)
- Semua TelemetryEvent di SubAgent.execute() juga ditambahi `metadata={"tool_name": "..."}` opsional

---

### 2.5 `main.py` — SSE endpoint tetap sama (tidak perlu perubahan)

**File:** `main.py` (line 114-130)

SSE endpoint sudah mengalirkan `TelemetryEvent` via `telemetry.subscribe()` dan `telemetry.emit()`. Field baru `metadata` akan otomatis ikut karena `event.dict()` di `core/telemetry.py:26` menserialize semua field.

**TIDAK PERLU PERUBAHAN di `main.py`.**

---

### 2.6 `core/telemetry.py` — Pastikan serialize metadata

**File:** `core/telemetry.py` (line 24-28)

**Current state:**
```python
async def emit(self, event: TelemetryEvent):
    data = event.dict()
    for queue in self.queues:
        await queue.put(data)
```

**Target (update ke Pydantic v2 `.model_dump()`):**
```python
async def emit(self, event: TelemetryEvent):
    data = event.model_dump()
    for queue in self.queues:
        await queue.put(data)
```

**Catatan:** `.dict()` deprecated di Pydantic v2. Ganti ke `.model_dump()`. Tidak mengubah behavior, hanya compliance.

---

## 3. Frontend — Daftar Perubahan

### 3.1 `stores/telemetryStore.ts` — Zustand store (FILE BARU)

**Path:** `frontend/src/stores/telemetryStore.ts`

**Install zustand dulu:**
```bash
cd frontend && pnpm add zustand
```

**Isi file:**
```typescript
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
```

---

### 3.2 `NarrativeStream.tsx` — SSE consumer (FILE BARU)

**Path:** `frontend/src/components/pemali/NarrativeStream.tsx`

**Spesifikasi:**
- Connect ke `EventSource('/api/telemetry')`
- Parse JSON → panggil `addEvent()` dari store
- Update `isConnected` status
- Reconnect otomatis setelah 3 detik jika disconnect
- Tidak render UI sendiri — hanya feed ke store
- Gunakan `"use client"` directive

```tsx
"use client";

import { useEffect, useRef } from "react";
import { useTelemetryStore } from "@/stores/telemetryStore";

export default function NarrativeStream() {
  const { addEvent, setConnected } = useTelemetryStore();
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const connect = () => {
      const es = new EventSource("/api/telemetry");

      es.onopen = () => setConnected(true);

      es.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data);
          addEvent(event);
        } catch (err) {
          console.error("SSE parse error:", err);
        }
      };

      es.onerror = () => {
        setConnected(false);
        es.close();
        setTimeout(connect, 3000);
      };

      esRef.current = es;
    };

    connect();

    return () => {
      if (esRef.current) esRef.current.close();
    };
  }, [addEvent, setConnected]);

  return null;
}
```

---

### 3.3 `NarrativeCard.tsx` — Render satu event narasi (FILE BARU)

**Path:** `frontend/src/components/pemali/NarrativeCard.tsx`

**Color mapping (PEMALI tokens):**
| State | Color | Background |
|-------|-------|------------|
| THINKING | `var(--state-thinking)` #8B5CF6 | `rgba(139,92,246,0.15)` |
| SPAWNING | `var(--state-spawning)` #3B82F6 | `rgba(59,130,246,0.15)` |
| EXECUTING | `var(--state-executing)` #10B981 | `rgba(16,185,129,0.15)` |
| ERROR | `var(--state-error)` #EF4444 | `rgba(239,68,68,0.15)` |
| DONE | `var(--state-complete)` #6EE7B7 | `rgba(110,231,183,0.15)` |
| IDLE | `var(--pemali-text-muted)` | transparent |

**Spesifikasi:**
- Card dengan border kiri berwarna state color
- Tampilkan `node_type` + `node_id` di header
- Tampilkan `narrative` sebagai body
- Tampilkan `metadata.tool_name` dan `metadata.duration_ms` jika ada (pill badge kecil)
- Tampilkan `timestamp` dalam format relatif / waktu Indonesia
- Framer Motion: slide in dari bawah, fade masuk

```tsx
"use client";

import { motion } from "framer-motion";
import { Cpu, Bot, Wrench, Clock } from "lucide-react";
import type { TelemetryEvent } from "@/stores/telemetryStore";

const stateConfig: Record<string, { color: string; bg: string }> = {
  THINKING: { color: "var(--state-thinking)", bg: "rgba(139,92,246,0.12)" },
  SPAWNING: { color: "var(--state-spawning)", bg: "rgba(59,130,246,0.12)" },
  EXECUTING: { color: "var(--state-executing)", bg: "rgba(16,185,129,0.12)" },
  ERROR: { color: "var(--state-error)", bg: "rgba(239,68,68,0.12)" },
  DONE: { color: "var(--state-complete)", bg: "rgba(110,231,183,0.12)" },
};

const nodeTypeIcon = {
  Manager: Bot,
  SubAgent: Cpu,
  Module: Wrench,
};

function formatTime(ts: number) {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function NarrativeCard({ event }: { event: TelemetryEvent }) {
  const config = stateConfig[event.state] || {
    color: "var(--pemali-text-muted)",
    bg: "transparent",
  };
  const Icon = nodeTypeIcon[event.node_type] || Cpu;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.2 }}
      className="flex gap-3 group"
    >
      <div className="relative flex flex-col items-center">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 border"
          style={{
            backgroundColor: config.bg,
            borderColor: config.color,
          }}
        >
          <Icon className="w-4 h-4" style={{ color: config.color }} />
        </div>
        <div
          className="w-px flex-1 mt-1"
          style={{ backgroundColor: `${config.color}40` }}
        />
      </div>

      <div className="flex-1 min-w-0 pb-4">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-xs font-semibold text-[var(--pemali-text-primary)]">
            {event.node_type === "Module"
              ? event.node_id
              : `${event.node_type} · ${event.node_id}`}
          </span>
          <span
            className="text-[9px] font-mono px-1.5 py-0.5 rounded border"
            style={{
              color: config.color,
              borderColor: `${config.color}40`,
              backgroundColor: config.bg,
            }}
          >
            {event.state}
          </span>
          <span className="text-[9px] font-mono text-[var(--pemali-text-muted)] ml-auto">
            {formatTime(event.timestamp)}
          </span>
        </div>

        <p className="text-[13px] text-[var(--pemali-text-secondary)] leading-relaxed">
          {event.narrative}
        </p>

        {event.metadata && (
          <div className="flex items-center gap-2 mt-2">
            {event.metadata.tool_name && (
              <span className="text-[10px] font-mono text-[var(--pemali-accent)] bg-[var(--pemali-accent-dim)] px-2 py-0.5 rounded">
                {event.metadata.tool_name}
              </span>
            )}
            {event.metadata.duration_ms !== undefined && (
              <span className="text-[10px] font-mono text-[var(--pemali-text-muted)] flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {event.metadata.duration_ms}ms
              </span>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
```

---

### 3.4 `DAGViewer.tsx` — Visualisasi progress DAG (FILE BARU)

**Path:** `frontend/src/components/pemali/DAGViewer.tsx`

**Spesifikasi:**
- Read events dari Zustand store
- Extract node IDs dan dependensi dari events
- Render sebagai horizontal flowchart dengan connecting lines
- Node state diambil dari event terbaru per node_id
- Library: pure SVG + Tailwind CSS (tidak perlu reactflow/library eksternal — kita render manual)

```tsx
"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { CheckCircle, Loader2, XCircle } from "lucide-react";
import { useTelemetryStore, type TelemetryEvent } from "@/stores/telemetryStore";

function extractDagNodes(events: TelemetryEvent[]) {
  const nodeStates = new Map<string, string>();
  const order: string[] = [];

  for (const evt of events) {
    if (!nodeStates.has(evt.node_id)) {
      order.push(evt.node_id);
    }
    nodeStates.set(evt.node_id, evt.state);
  }

  return order.map((id) => ({
    id,
    label: id.replace("_", " "),
    state: nodeStates.get(id) || "IDLE",
  }));
}

const stateColor: Record<string, string> = {
  IDLE: "var(--pemali-text-muted)",
  THINKING: "var(--state-thinking)",
  SPAWNING: "var(--state-spawning)",
  EXECUTING: "var(--state-executing)",
  DONE: "var(--state-complete)",
  ERROR: "var(--state-error)",
};

export default function DAGViewer() {
  const events = useTelemetryStore((s) => s.events);
  const nodes = useMemo(() => extractDagNodes(events), [events]);

  if (nodes.length === 0) return null;

  return (
    <div className="bg-[var(--pemali-surface)] rounded-2xl border border-[var(--pemali-border)] p-5">
      <div className="text-[9px] font-mono text-[var(--pemali-text-muted)] uppercase tracking-widest mb-4">
        Agent Pipeline — DAG
      </div>

      <div className="relative py-4">
        {/* SVG connecting lines */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          {nodes.slice(0, -1).map((node, i) => (
            <line
              key={node.id}
              x1={`${((i + 0.8) / nodes.length) * 100}%`}
              y1="50%"
              x2={`${((i + 1.2) / nodes.length) * 100}%`}
              y2="50%"
              stroke={
                node.state === "DONE"
                  ? "var(--state-complete)"
                  : "var(--pemali-border)"
              }
              strokeWidth="1.5"
              strokeDasharray={node.state === "DONE" ? "0" : "4 4"}
            />
          ))}
        </svg>

        {/* Nodes */}
        <div className="relative z-10 flex justify-between items-center">
          {nodes.map((node) => (
            <motion.div
              key={node.id}
              className="flex flex-col items-center gap-2"
              animate={{
                scale: node.state === "EXECUTING" ? [1, 1.05, 1] : 1,
              }}
              transition={{
                repeat: node.state === "EXECUTING" ? Infinity : 0,
                duration: 1.5,
              }}
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center border-2 transition-colors"
                style={{
                  borderColor: stateColor[node.state],
                  backgroundColor: `${stateColor[node.state]}15`,
                }}
              >
                {node.state === "DONE" ? (
                  <CheckCircle
                    className="w-5 h-5"
                    style={{ color: stateColor[node.state] }}
                  />
                ) : node.state === "ERROR" ? (
                  <XCircle
                    className="w-5 h-5"
                    style={{ color: stateColor[node.state] }}
                  />
                ) : node.state === "EXECUTING" || node.state === "THINKING" ? (
                  <Loader2
                    className="w-5 h-5 animate-spin"
                    style={{ color: stateColor[node.state] }}
                  />
                ) : (
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: stateColor[node.state] }}
                  />
                )}
              </div>
              <span
                className="text-[9px] font-mono uppercase tracking-widest"
                style={{ color: stateColor[node.state] }}
              >
                {node.label}
              </span>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

### 3.5 Wire ke `dashboard/page.tsx`

**File:** `frontend/src/app/dashboard/page.tsx`

**Perubahan yang diperlukan:**
1. Import `NarrativeStream` dan render di top-level layout (hidden component, hanya SSE feed)
2. Tambah tab "Narrative" di tab bar (sejajar dengan Agents, Telemetry, Module Output)
3. Render `NarrativeCard` untuk setiap event di store
4. Replace DAG visualizer lama dengan `DAGViewer` baru yang baca dari store

**Langkah spesifik:**

1. **Tambah import di atas file:**
```typescript
import NarrativeStream from "@/components/pemali/NarrativeStream";
import NarrativeCard from "@/components/pemali/NarrativeCard";
import DAGViewer from "@/components/pemali/DAGViewer";
import { useTelemetryStore } from "@/stores/telemetryStore";
```

2. **Render `<NarrativeStream />` di dalam `<main>` — di mana saja, komponen ini invisible (return null):**
   Tambah di baris setelah `<StatusBar>`:
```tsx
<NarrativeStream />
```

3. **Baca dari store di dalam komponen Dashboard:**
```typescript
const narrativeEvents = useTelemetryStore((s) => s.events);
const isSSEConnected = useTelemetryStore((s) => s.isConnected);
```

4. **Tambah tab "Narrative" di tab bar (line 330-349):**
   Tambah item ke array tab:
```typescript
{ id: 'narrative', label: 'Narrative', icon: MessageSquare },
```
   Import `MessageSquare` dari lucide-react di line 5-12.

5. **Tambah render case untuk tab "narrative":**
   Di antara case `'telemetry'` dan `'modules'`:
```tsx
{activeTab === 'narrative' && (
  <motion.div
    key="narrative-tab"
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    className="space-y-1"
  >
    {narrativeEvents.length === 0 && (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <MessageSquare className="w-10 h-10 text-[var(--pemali-text-muted)] mb-3" />
        <div className="text-sm text-[var(--pemali-text-muted)]">Belum ada narasi agent</div>
        <div className="text-[10px] font-mono text-[var(--pemali-text-muted)] mt-1 uppercase tracking-widest">
          {isSSEConnected ? 'Menunggu aktivitas agent...' : 'SSE disconnected'}
        </div>
      </div>
    )}
    {[...narrativeEvents].reverse().map((event, i) => (
      <NarrativeCard key={`${event.trace_id}-${event.timestamp}-${i}`} event={event} />
    ))}
  </motion.div>
)}
```

6. **Replace DAG visualizer (line 363-428):**
   Ganti seluruh div DAG visualizer manual dengan:
```tsx
<DAGViewer />
```
   Hapus state `dagNodes`, `dagActive`, dan semua kode terkait (line 95-101, state di useState, animasi manual).

---

## 4. Testing

### 4.1 `tests/test_narrative.py` — Integration test (FILE BARU)

**Path:** `tests/test_narrative.py`

**Spesifikasi test:**
1. `test_telemetry_event_has_metadata` — pastikan TelemetryEvent bisa punya metadata
2. `test_manager_system_prompt_has_contract` — pastikan prompt Manager ada NARRATIVE CONTRACT
3. `test_subagent_system_prompt_has_contract` — pastikan prompt SubAgent ada NARRATIVE CONTRACT
4. `test_tool_execution_records_duration_ms` — pastikan _execute_tool mencatat duration_ms
5. `test_telemetry_stream_includes_metadata` — pastikan SSE stream serialize metadata
6. `test_rag_context_in_prompt` — pastikan RAG context masuk ke prompt
7. `test_empty_rag_context_handling` — pastikan prompt tetap valid tanpa RAG context
8. `test_error_tool_records_duration` — error pun tetap catat duration

**Kerangka test:**
```python
import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from core.models import TelemetryEvent, NodeState
from core.orchestrator import SubAgent, TaskIntent, PemaliOrchestrator

class TestTelemetryMetadata:
    def test_event_with_metadata(self):
        evt = TelemetryEvent(
            trace_id="tr-123",
            node_id="geo_worker",
            node_type="Module",
            state=NodeState.EXECUTING,
            narrative="Test",
            metadata={"tool_name": "satellite", "duration_ms": 245.5}
        )
        data = evt.model_dump()
        assert data["metadata"]["tool_name"] == "satellite"
        assert data["metadata"]["duration_ms"] == 245.5

    def test_event_without_metadata(self):
        evt = TelemetryEvent(
            trace_id="tr-123",
            node_id="geo_worker",
            node_type="Module",
            state=NodeState.DONE,
            narrative="Done"
        )
        data = evt.model_dump()
        assert data["metadata"] is None

class TestNarrativeContract:
    def test_manager_prompt_has_contract(self):
        orchestrator = PemaliOrchestrator("test-session")
        # Akses sys_prompt via inspect atau mock run()
        # Assert "NARRATIVE CONTRACT" ada di prompt
        # Assert "CARA MEMBACA RAG CONTEXT" ada di prompt
        pass

    def test_rag_context_in_prompt(self):
        pass

class TestDurationTracking:
    @pytest.mark.asyncio
    async def test_tool_duration_recorded(self):
        pass

    @pytest.mark.asyncio
    async def test_error_tool_records_duration(self):
        pass
```

**Jalankan test:**
```bash
cd /home/rio/Documents/PEMALI && python -m pytest tests/test_narrative.py -v
```

---

## 5. Implementation Checklist (Urutan Pengerjaan)

### Fase 1 — Backend (3-5 jam)

- [ ] **Task 1:** `core/models.py` — tambah field `metadata: Optional[Dict[str, Any]]` ke TelemetryEvent
- [ ] **Task 2:** `core/telemetry.py` — ganti `.dict()` ke `.model_dump()` di emit()
- [ ] **Task 3:** `core/orchestrator.py` — tambah `import time` di header
- [ ] **Task 4:** `core/orchestrator.py` — update Manager system prompt (NARRATIVE CONTRACT + RAG reading)
- [ ] **Task 5:** `core/orchestrator.py` — update SubAgent system prompt (NARRATIVE CONTRACT + state machine)
- [ ] **Task 6:** `core/orchestrator.py` — tambah duration tracking di `_execute_tool()`

### Fase 2 — Frontend (8-12 jam)

- [ ] **Task 7:** `cd frontend && pnpm add zustand`
- [ ] **Task 8:** `stores/telemetryStore.ts` — buat Zustand store (FILE BARU)
- [ ] **Task 9:** `components/pemali/NarrativeStream.tsx` — SSE consumer (FILE BARU)
- [ ] **Task 10:** `components/pemali/NarrativeCard.tsx` — render card (FILE BARU)
- [ ] **Task 11:** `components/pemali/DAGViewer.tsx` — visualisasi DAG (FILE BARU)
- [ ] **Task 12:** `app/dashboard/page.tsx` — wire semua komponen ke dashboard

### Fase 3 — Testing (4-6 jam)

- [ ] **Task 13:** `tests/test_narrative.py` — integration test (FILE BARU)
- [ ] **Task 14:** Jalankan `python -m pytest tests/test_narrative.py -v` pastikan semua pass
- [ ] **Task 15:** Jalankan `python -m pytest tests/ -v` pastikan semua 35 test existing + new test pass
- [ ] **Task 16:** Jalankan `cd frontend && pnpm build` pastikan tidak ada error

---

## 6. File yang Akan Diubah/Dibuat

| File | Aksi | Deskripsi |
|------|------|-----------|
| `SPRINT_3_GUIDE.md` | NEW | Dokumen ini |
| `core/models.py` | EDIT | Tambah field metadata ke TelemetryEvent |
| `core/telemetry.py` | EDIT | Ganti .dict() ke .model_dump() |
| `core/orchestrator.py` | EDIT | System prompt contracts + duration tracking + import time |
| `main.py` | NO CHANGE | SSE endpoint sudah ok |
| `frontend/src/stores/telemetryStore.ts` | NEW | Zustand store |
| `frontend/src/components/pemali/NarrativeStream.tsx` | NEW | SSE consumer |
| `frontend/src/components/pemali/NarrativeCard.tsx` | NEW | Narasi card |
| `frontend/src/components/pemali/DAGViewer.tsx` | NEW | DAG visualizer |
| `frontend/src/app/dashboard/page.tsx` | EDIT | Wire komponen + tab narrative |
| `frontend/package.json` | EDIT | Tambah zustand dependency |
| `tests/test_narrative.py` | NEW | Integration test |
| `frontend/src/stores/` | NEW DIRECTORY | Directory for Zustand stores |

---

## 7. Verifikasi Final

```bash
# Backend
cd /home/rio/Documents/PEMALI
python -m pytest tests/ -v
# Expected: 35 existing + 8 new = 43 passing

# Frontend
cd /home/rio/Documents/PEMALI/frontend
pnpm build
# Expected: no errors
```

---

## 8. Catatan Penting

- **TelemetryEvent.metadata** bersifat opsional (`Optional[Dict]`). Event tanpa metadata tetap valid — untuk backward compatibility.
- **Zustand store** bukan React context. Bisa diakses dari komponen mana pun tanpa provider wrapper.
- **DAGViewer** tidak perlu library eksternal. Render SVG + div manual untuk kontrol penuh styling.
- **Semua narasi bahasa Indonesia.** Tidak boleh campur English di system prompt.
- **RAG context** tetap disisipkan di System Prompt Manager (bukan di User Prompt), dengan instruksi cara membaca yang jelas.
- **Jangan hapus TelemetryFeed.tsx yang existing** — akan tetap dipakai di tab "Telemetry". NarrativeStream terpisah.

---

*Dokumen dibuat: 2025-05-09. Pemilik: PEMALI Core Team.*
