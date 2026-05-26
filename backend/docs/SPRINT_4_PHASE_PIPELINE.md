# PEMALI v2 — 4-Fase Pipeline Architecture

> Spec untuk Sprint 3: Narrative + SDUI + Telemetry  
> Dibuat: 15 Mei 2026  
> Mode: Build-ready spec

---

## 1. Overview

Mengganti pipeline linear 2-fase (Plan → Synthesis) menjadi **4-fase chain** dengan re-spawn loop.

```
Sebelum:  Planning ──→ Synthesis ──→ Done
Sesudah:  Planning ──→ Execute ──→ Validate ──→ Synthesis ──→ Done
                              ↑                    │
                              └── Re-spawn loop ───┘
```

---

## 2. Phase Definitions

### 2.1 Planning (Fase 1)

| Properti | Value |
|----------|-------|
| **Trigger** | User mengirim prompt via POST `/api/stream` |
| **LLM call** | Ya — 1x ke OpenRouter (`create_audit_plan` tool) |
| **Input context** | `user_prompt` + RAG (ChromaDB + Knowledge Graph) |
| **Output** | `MasterPlan` (list of `TaskIntent`) |
| **Narrative** | LLM-generated narasi tentang analisis request user |
| **THINKING count** | 2-4x (LLM streaming chunk → narasi berkembang) |
| **SSE metadata** | `{"phase": "planning"}` |

**State flow dalam fase:**
```
THINKING → THINKING → THINKING (LLM selesai)
```

**CONTOH SSE OUTPUT:**
```json
{"node_id":"manager","node_type":"Manager","state":"THINKING",
 "narrative":"Menganalisis permintaan user untuk audit Gianyar...",
 "metadata":{"phase":"planning"}}
```

### 2.2 Execute (Fase 2)

| Properti | Value |
|----------|-------|
| **Trigger** | Planning selesai, `MasterPlan` siap |
| **LLM call** | Tidak — murni orchestrator |
| **Input context** | `MasterPlan`, `user_prompt` |
| **Output** | `raw_results` (data dari sub-agent + tools) |
| **Narrative** | Generated orchestrator: agent mana yang dispown, progress, done |
| **THINKING count** | 3-10x (1 per spawn, 1 per agent DONE, 1 all-done) |
| **SSE metadata** | `{"phase": "execute", "phase_step": "spawning"|"progress"|"complete"}` |

**State flow dalam fase:**
```
THINKING (spawning) → [sub-agent THINKING → EXECUTING → DONE]*
                    → THINKING (progress per agent) 
                    → THINKING (all-complete)
```

*Sub-agent THINKING iterations pakai replace mode — hanya latest yang render.

**CONTOH SSE OUTPUT:**
```json
// Spawning
{"node_id":"manager","node_type":"Manager","state":"THINKING",
 "narrative":"Menjalankan 4 agent: geo_agent, fire_agent, water_agent, osint_agent...",
 "metadata":{"phase":"execute","phase_step":"spawning","task_count":4}}

// Progress per agent selesai
{"node_id":"manager","node_type":"Manager","state":"THINKING",
 "narrative":"geo_agent selesai. Menunggu fire_agent, water_agent, osint_agent...",
 "metadata":{"phase":"execute","phase_step":"progress","done":["geo_agent"],"pending":["fire_agent","water_agent","osint_agent"]}}

// All complete
{"node_id":"manager","node_type":"Manager","state":"THINKING",
 "narrative":"Semua 4 agent selesai ejecutif. Masuk ke validasi.",
 "metadata":{"phase":"execute","phase_step":"complete","success_count":4,"fail_count":0}}
```

### 2.3 Validate (Fase 3) — BARU

| Properti | Value |
|----------|-------|
| **Trigger** | Execute selesai (semua sub-agent DONE/ERROR) |
| **LLM call** | Tidak untuk decision — LLM boleh override via re-spawn (opsional) |
| **Input context** | `MasterPlan`, `raw_results`, agent narratives |
| **Output** | `validated_results`, `final_failed_tasks` |
| **Narrative** | Generated orchestrator + optional LLM override |
| **THINKING count** | 3-8x |
| **SSE metadata** | `{"phase": "validate", "phase_step": "checking"|"anomaly"|"re-spawn"|"re-spawn-done"|"valid"}` |

**Logic validasi:**
```
for setiap result dalam raw_results:
    if result memiliki _ERROR_:
        → flag anomaly, siapkan re-spawn
    elif result kosong atau "data not found":
        → flag anomaly, siapkan re-spawn
    else:
        → valid

if ada anomaly:
    for setiap anomaly:
        if re-spawn_count < max_re-spawn (2):
            → emit THINKING("Anomali di {agent}, re-spawn dengan param baru")
            → spawn ulang sub-agent spesifik tsb
            → tunggu hasil
            → re-spawn_count++
        else:
            → emit THINKING("{agent} gagal 2x re-spawn, lanjut partial")
else:
    → emit THINKING("Semua data valid, lanjut synthesis")
```

**State flow dalam fase:**
```
THINKING (checking) → THINKING (anomaly detected) 
    → [re-spawn loop: THINKING (re-spawning) → [sub-agent runs] → THINKING (re-spawn done)]
    → THINKING (all-valid / partial-valid)
```

**CONTOH SSE OUTPUT:**
```json
// Start checking
{"node_id":"manager","node_type":"Manager","state":"THINKING",
 "narrative":"Memvalidasi data dari 4 agent...",
 "metadata":{"phase":"validate","phase_step":"checking"}}

// Anomaly detected
{"node_id":"manager","node_type":"Manager","state":"THINKING",
 "narrative":"water_agent data kosong untuk Sungai Ayung. Re-spawn water_agent dengan rentang waktu berbeda.",
 "metadata":{"phase":"validate","phase_step":"anomaly","agent":"water_agent","reason":"empty_data"}}

// Re-spawn done
{"node_id":"manager","node_type":"Manager","state":"THINKING",
 "narrative":"Re-spawn water_agent selesai. Data valid. Lanjut synthesis.",
 "metadata":{"phase":"validate","phase_step":"re-spawn-done","agent":"water_agent","attempt":1,"status":"success"}}

// All valid (no anomalies)
{"node_id":"manager","node_type":"Manager","state":"THINKING",
 "narrative":"Semua data dari 4 agent valid. Lanjut synthesis.",
 "metadata":{"phase":"validate","phase_step":"valid"}}
```

### 2.4 Synthesis (Fase 4)

| Properti | Value |
|----------|-------|
| **Trigger** | Validate selesai |
| **LLM call** | Ya — streaming ke OpenRouter (`generate_report` tool) |
| **Input context** | `user_prompt`, `MasterPlan`, `raw_results`, `validated_results`, `validation_narrative` |
| **Output** | Final report text (streaming) |
| **Narrative** | LLM-generated synthesis stream |
| **THINKING count** | 1-2x |
| **SSE metadata** | `{"phase": "synthesis"}` |

**Input enhanced untuk synthesis (context propagation):**
```python
synth_input = {
    "user_request": prompt,                    # Baru: prompt asli user
    "plan_summary": plan_summary,              # Baru: tugas yg direncanakan
    "execution_results": {                     # Enhanced
        "successful": [...],
        "failed": [...],
    },
    "validation_summary": validation_narrative,  # Baru: hasil validasi
    "re_spawn_attempts": re_spawn_log,          # Baru: catatan re-spawn
}
```

**CONTOH SSE OUTPUT:**
```json
{"node_id":"manager","node_type":"Manager","state":"THINKING",
 "narrative":"Berdasarkan data dari 4 agent yang telah divalidasi...",
 "metadata":{"phase":"synthesis"}}
```

### 2.5 DONE

| Properti | Value |
|----------|-------|
| **Trigger** | Synthesis selesai |
| **LLM call** | Tidak |
| **Narrative** | Full report text |
| **SSE metadata** | `{"phase": "done", "type": "final_report", "session_id": "..."}` |

---

## 3. Context Propagation

Tiap fase terima output dari **semua fase sebelumnya** sebagai input context.

```
user_prompt ──┬───────────────┬───────────────┬──────────────┐
              │               │               │               │
              ▼               ▼               ▼               ▼
           Planning ───→ Execute ──────→ Validate ──────→ Synthesis
              │               │               │               │
           MasterPlan    raw_results    validated_results  final_report
           narrative      narratives     re_spawn_log
```

| Fase | Input Context |
|------|-------------|
| **Planning** | `user_prompt`, RAG (ChromaDB + Knowledge Graph) |
| **Execute** | `user_prompt`, `MasterPlan` |
| **Validate** | `user_prompt`, `MasterPlan`, `raw_results`, agent_narratives |
| **Synthesis** | `user_prompt`, `MasterPlan`, `raw_results`, `validated_results`, `validation_narrative`, `re_spawn_log` |

### Kenapa ini penting:

1. **Validate** perlu `MasterPlan` untuk evaluasi: "Agent x direncanakan untuk water quality, tapi hasil kosong → anomali"
2. **Synthesis** perlu full picture: "User minta audit Gianyar → 4 agent direncanakan → 3 sukses, 1 gagal → water gagal meski re-spawn → laporan dengan catatan partial"

### Narrative accumulator:
```python
# Narasi tiap fase disimpan untuk dipass ke fase berikutnya
context_chain = {
    "user_request": prompt,
    "plan": plan,                      # MasterPlan
    "plan_narrative": plan_narrative,   # Narasi dari Planning
    "execute_narrative": [],            # List narasi progress Execute
    "raw_results": {},                  # shared_context
    "validate_narrative": [],           # List narasi validasi
    "re_spawn_log": [],                 # [{agent, attempt, status, reason}]
}
```

---

## 4. SSE Event Contract

### 4.1 Event Types

| Event field | Value | Konsumen frontend |
|-------------|-------|-------------------|
| `event: state` | TelemetryEvent dict | DAGCanvas, NarrativeCard |
| `event: token` | `{node_id, content}` | ChatInput (typing effect) |

### 4.2 State Event Structure

```typescript
interface TelemetryEvent {
  trace_id: string
  node_id: string          // "manager" | agent_id | tool_name
  node_type: string        // "Manager" | "SubAgent" | "Module" | "System"
  state: NodeState         // "THINKING" | "SPAWNING" | "EXECUTING" | "ERROR" | "DONE"
  narrative: string
  timestamp: number
  metadata?: {
    phase?: string          // "planning" | "execute" | "validate" | "synthesis" | "done"
    phase_step?: string     // "spawning" | "progress" | "complete" | "checking" | "anomaly" | "re-spawn" | "re-spawn-done" | "valid"
    task_count?: number     // Jumlah task/agent yang dispown (Execute spawning)
    success_count?: number  // Agent sukses (Execute complete)
    fail_count?: number
    done?: string[]         // Agent yang sudah selesai (Execute progress)
    pending?: string[]      // Agent yang masih running (Execute progress)
    agent?: string          // Agent yang mengalami anomali (Validate)
    reason?: string         // Alasan anomaly (Validate)
    attempt?: number        // Re-spawn attempt number (Validate)
    status?: string         // "success" | "failed" (Validate re-spawn)
    type?: string           // "final_report" (Done)
    session_id?: string     // (Done)
  }
}
```

### 4.3 Lite Event (opsional — untuk token streaming)

```typescript
interface TokenEvent {
  _sse_event: "token"
  node_id: string
  content: string
}
```

---

## 5. Frontend Architecture

### 5.1 Layout Grid

```
┌──────────────────────────────────────────────────────┐
│ STATUS BAR: model | worker | last tick                │
├────────────────────────────────┬─────────────────────┤
│                                │                     │
│   OBSERVATION ZONE (60%)       │ INTERACTION (40%)   │
│                                │                     │
│  ┌─ MANAGER COMPOUND CARD ──┐  │ ┌─ CHAT INPUT ────┐ │
│  │ Phase chain ●──○──○──○  │  │ │ "Audit Gianyar"  │ │
│  │ ┌─ THINKING (latest) ──┐ │  │ └─────────────────┘ │
│  │ │ "...narrative..."    │  │ │ ┌─ HISTORY ───────┐ │
│  │ └──────────────────────┘  │ │ │ session-1       │ │
│  │ Progress ●──○ Step 4/12  │  │ │ session-2       │ │
│  └──────────────────────────┘  │ └─────────────────┘ │
│                                │                     │
│  ┌─ SUB-AGENTS GRID ────────┐  │                     │
│  │ geo │ fire │ water │ osint│  │                     │
│  └──────────────────────────┘  │                     │
│                                │                     │
└────────────────────────────────┴─────────────────────┘
```

### 5.2 Component Tree

```
DashboardPage
├── StatusBar
│   ├── model: string
│   ├── workerStatus: "online"|"offline"
│   └── lastTick: timestamp
│
├── ObservationZone (60%)
│   ├── ManagerCompoundCard
│   │   ├── PhaseChain          // Planning ●──○ Execute ●──○ ...
│   │   ├── PhaseContent        // AnimatePresence: THINKING narration
│   │   └── ProgressBar         // ●──○──○──○ Step X/Y
│   │
│   ├── SubAgentGrid
│   │   └── SubAgentCard[]      // horizontal flex, persist
│   │       ├── AgentHeader     // name + state badge
│   │       └── AgentBody       // latest THINKING | EXECUTING | DONE
│   │
│   └── ModuleOutput            // final report display (markdown)
│
└── InteractionZone (40%)
    ├── ChatInput
    │   ├── Textarea
    │   └── SendButton
    └── SessionList
```

### 5.3 Manager Compound Card — Key Behaviors

| Behavior | Spec |
|----------|------|
| **Card type** | Persistent — 1 card per session |
| **Phase chain** | Horizontal bar di atas card: `Planning ●──○ Execute ●──○ Validate ○──○ Synthesis` |
| **THINKING display** | Hanya **latest** narasi yang tampil (replace previous, fade morph) |
| **Transition** | Framer Motion `AnimatePresence` mode="wait" |
| **Duration** | 400ms, ease `[0.0, 0.0, 0.2, 1]` (smooth deceleration) |
| **Progress bar** | Bottom-left, `●──○──○──○──○ Step 4/12` |
| **Expand/collapse** | Auto-expand current phase saat THINKING baru. User bisa collapse manual. |
| **Re-spawn behavior** | Phase chain nambah segmen: `...Validate ●──○ Execute(water) ●──○ Synthesis` |

### 5.4 SubAgent Card — Key Behaviors

| Behavior | Spec |
|----------|------|
| **Layout** | Horizontal flex grid, max 5 card per row |
| **Lifecycle** | Persist selamanya (muncul saat di-spawn, tidak hilang) |
| **State badge** | Warna sesuai `--state-*` token: thinking=purple, executing=emerald, done=light emerald, error=red |
| **THINKING display** | Hanya **latest** narasi (replace, fade morph) |
| **Min height** | Fluid, min 120px |
| **Re-spawn** | Agent yang di-re-spawn muncul sebagai card baru (water_v2) di samping yang lama |

### 5.5 Progressive Steps Counter

```typescript
// Total steps = jumlah unik event dari agent yang berbeda
const totalSteps = events.filter(e => e.node_type !== "Module" && e.state !== "IDLE").length
const currentStep = events.filter(e => e.state !== "IDLE" && e.node_id !== "manager").length

// Render: ●───○───○───○───○─── Stage 4/12
```

---

## 6. Backend Implementation Plan

### 6.1 File: `backend/core/orchestrator.py`

#### Modifikasi yang ada:

| Lokasi | Yang diubah | Detail |
|--------|-----------|--------|
| Line 647-650 | THINKING Planning | Tambah `metadata={"phase":"planning"}` |
| Line 669-672 | SPAWNING → THINKING | Ganti state ke THINKING, tambah metadata execute + agent list |
| Line 710-763 | DAG loop | Tambah emit THINKING progress setiap sub-agent selesai |
| Line 764-765 | Post-DAG | Tambah emit THINKING "all done" dengan summary |
| Line 866-869 | THINKING Synthesis | Tambah `metadata={"phase":"synthesis"}` |
| Line 908-912 | DONE | Merge `phase: "done"` ke metadata existing |

#### Kode baru (Fase 3 Validate):

| Lokasi | Yang ditambah | Detail |
|--------|-------------|--------|
| Setelah line 765 | `_phase_validate()` method | ~50 baris: cek anomaly → re-spawn loop → narasi |
| Line 767-784 | Enhanced synthesis input | Tambah context propagation fields |
| Line 517 | `context_chain` dict | Akumulator untuk context propagation |

#### Struktur `_phase_validate()`:

```python
async def _phase_validate(self, shared_context, failed_tasks, plan, trace_id):
    """Fase 3: Validasi hasil agent, trigger re-spawn jika anomali."""
    re_spawn_log = []
    max_re_spawn = 2
    
    await telemetry.emit(TelemetryEvent(
        trace_id=trace_id, node_id="manager", node_type="Manager",
        state=NodeState.THINKING,
        narrative=f"Memvalidasi data dari {len(shared_context)} agent...",
        metadata={"phase": "validate", "phase_step": "checking"}
    ))
    
    anomalies = []
    for task_id, data in shared_context.items():
        if "_ERROR_" in data:
            anomalies.append((task_id, data, "error"))
        elif not data or data == {} or "data not found" in str(data).lower():
            anomalies.append((task_id, data, "empty"))
    
    for task_id, data, reason in anomalies:
        for attempt in range(1, max_re_spawn + 1):
            agent = data.get("_ERROR_", {}).get("agent", task_id) if reason == "error" else task_id
            # emit anomaly detected
            await telemetry.emit(TelemetryEvent(
                trace_id=trace_id, node_id="manager", node_type="Manager",
                state=NodeState.THINKING,
                narrative=f"Anomali di {agent} ({reason}). Re-spawn attempt {attempt}/{max_re_spawn}.",
                metadata={"phase":"validate","phase_step":"anomaly","agent":agent,"reason":reason,"attempt":attempt}
            ))
            # re-execute sub-agent
            result = await self._re_spawn_agent(task_id, agent, plan, trace_id)
            if not self._is_error_response(result):
                shared_context[task_id] = result
                del failed_tasks.get(task_id, {})
                await telemetry.emit(TelemetryEvent(
                    trace_id=trace_id, node_id="manager", node_type="Manager",
                    state=NodeState.THINKING,
                    narrative=f"Re-spawn {agent} sukses pada attempt {attempt}.",
                    metadata={"phase":"validate","phase_step":"re-spawn-done","agent":agent,"attempt":attempt,"status":"success"}
                ))
                re_spawn_log.append({"agent": agent, "attempt": attempt, "status": "success", "reason": reason})
                break
        else:
            # Max re-spawn reached
            await telemetry.emit(TelemetryEvent(...))
            re_spawn_log.append({"agent": agent, "attempt": max_re_spawn, "status": "failed", "reason": reason})
    
    # Final validate narrative
    if anomalies:
        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="manager", node_type="Manager",
            state=NodeState.THINKING,
            narrative=f"Validasi selesai. {len(shared_context) - len(failed_tasks)}/{len(shared_context)} agent sukses. Lanjut synthesis.",
            metadata={"phase":"validate","phase_step":"valid"}
        ))
    else:
        await telemetry.emit(TelemetryEvent(...narrative="Semua data valid. Lanjut synthesis."...))
    
    return shared_context, failed_tasks, re_spawn_log
```

#### Re-spawn logic helper:

```python
async def _re_spawn_agent(self, task_id, agent_name, plan, trace_id):
    """Re-spawn satu sub-agent spesifik."""
    all_manifests = registry.get_all_manifests()
    scoped = get_scoped_manifests(agent_name, all_manifests)
    tools = [{"type": "function", "function": m} for m in scoped]
    
    task = next((t for t in plan.tasks if t.task_id == task_id), None)
    if not task:
        return ErrorResponse(status="VALIDATE_ERROR", ...).model_dump()
    
    sub = SubAgent(task, self.session_id, tools, trace_id)
    return await execute_subagent_with_safety(sub, trace_id, timeout=45)
```

---

## 7. Phase Chain & Re-spawn Behavior

### 7.1 Normal flow (no anomalies)

```
Planning ──→ Execute ──→ Validate ──→ Synthesis ──→ Done
   2-4           3-10         3-5          1-2          1
  THINKING      THINKING     THINKING     THINKING     event
```

### 7.2 Flow with re-spawn (water anomaly)

```
Planning ──→ Execute ──→ Validate ──→ Execute(water) ──→ Synthesis ──→ Done
```
Tahapan:
1. Planning: bikin plan 4 agent
2. Execute: spawn 4 agent, kumpulin hasil
3. Validate: deteksi water kosong → re-spawn water
4. Execute(water): spawn ulang water_agent
5. Synthesis: generate report dari 3 sukses + 1 re-spawn
6. Done

**Ini bukan re-entry Execute — tapi segmen baru di chain.**

### 7.3 Frontend render untuk re-spawn

```
Phase chain:
Planning ●──○ Execute ●──○ Validate ●──○ Execute(water) ●──○ Synthesis

Sub-agent cards:
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐
│ geo      │ │ fire     │ │ water    │ │ osint    │ │ water (v2)     │
│ [DONE ✓] │ │ [DONE ✓] │ │ [ERROR]  │ │ [DONE ✓] │ │ [THINKING ●]   │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └───────────────┘
```

---

## 8. Data Structures (Backend)

### 8.1 TelemetryEvent metadata spec

```python
# Manager events metadata
{
    "phase": "planning|execute|validate|synthesis|done",
    "phase_step": "spawning|progress|complete|checking|anomaly|re-spawn|re-spawn-done|valid",
    # phase-specific fields below (optional)
    "task_count": int,        # phase=execute, step=spawning
    "success_count": int,     # phase=execute, step=complete
    "fail_count": int,        # phase=execute, step=complete
    "done": ["agent_id",...],  # phase=execute, step=progress
    "pending": ["agent_id",...],  # phase=execute, step=progress
    "agent": "water_agent",   # phase=validate
    "reason": "empty_data",   # phase=validate
    "attempt": 1,             # phase=validate
    "status": "success",      # phase=validate
    "type": "final_report",   # phase=done
    "session_id": "sess-..."  # phase=done
}
```

### 8.2 NodeState enum (no changes needed)

```python
class NodeState(str, Enum):
    IDLE = "IDLE"           # Initial
    THINKING = "THINKING"   # LLM reasoning / orchestrator narrative
    # SPAWNING deprecated — replaced by THINKING+phase:execute
    EXECUTING = "EXECUTING" # Tool/module running
    ERROR = "ERROR"         # Failure
    DONE = "DONE"           # Complete
```

`SPAWNING` tetap di enum tapi gak dipakai — Manager pakai `THINKING + metadata.phase`.

---

## 9. Frontend Implementation Plan

### 9.1 File: `frontend/src/app/dashboard/page.tsx`

#### Current structure (yang perlu di-refactor):
```
- SSE event parser
- flat timeline render
- DAGCanvas (dagre)
- ChatInput
- Sidebar
```

#### Target structure:
```
- SSE event parser (unchanged)
- SSE event grouper → groupBy(events, "node_id")
- ManagerCompoundCard (BARU)
  - PhaseChain component
  - PhaseContent (AnimatePresence)
  - ProgressBar
- SubAgentGrid (BARU)
  - SubAgentCard[] (rendered dari grouped events)
- ModuleOutput (unchanged for final report)
- ChatInput (unchanged)
- Sidebar (unchanged)
```

### 9.2 Zustand Store Changes

```typescript
// telemetryStore.ts additions
interface TelemetryState {
  // ... existing ...
  
  // New: grouped events for compound card rendering
  eventsByAgent: Record<string, TelemetryEvent[]>
  
  // New: current phase for Manager
  managerPhase: string | null  // "planning"|"execute"|"validate"|"synthesis"|"done"
  
  // New: phase chain segments for progress bar
  phaseChain: PhaseSegment[]
  
  // New: sub-agent cards to render
  subAgents: SubAgentState[]
}

interface PhaseSegment {
  phase: string
  step: string
  narrative: string
  agent?: string  // for re-spawn segments
}

interface SubAgentState {
  nodeId: string
  currentState: NodeState
  narrative: string
  metadata?: Record<string, any>
}
```

### 9.3 ManagerCompoundCard Component Spec

```tsx
// Pseudocode
function ManagerCompoundCard({ events }) {
  const phases = useMemo(() => {
    // Extract unique phases from manager events
    // Phase changes when metadata.phase changes
  }, [events])
  
  const currentPhase = phases[phases.length - 1]
  const currentThinking = events.filter(e => e.metadata?.phase === currentPhase).slice(-1)[0]
  
  return (
    <div className="pemali-card">
      <PhaseChain phases={phases} currentPhase={currentPhase} />
      <AnimatePresence mode="wait">
        <motion.div
          key={currentThinking.narrative}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.4, ease: [0.0, 0.0, 0.2, 1] }}
        >
          <p>{currentThinking.narrative}</p>
        </motion.div>
      </AnimatePresence>
      <ProgressBar current={currentStep} total={totalSteps} />
    </div>
  )
}
```

### 9.4 PhaseChain Component Spec

```tsx
function PhaseChain({ phases, currentPhase }) {
  // Renders: Planning ●──○ Execute ●──○ Validate ○──○ Synthesis
  return (
    <div className="flex items-center gap-1">
      {phases.map((phase, i) => (
        <Fragment key={phase.id}>
          <span className={`${phase.phase === currentPhase ? 'text-pemali-accent' : 'text-pemali-text-muted'}`}>
            {phase.label}
          </span>
          {i < phases.length - 1 && (
            <span className="text-pemali-text-muted">
              {phase.phase === currentPhase ? '●──○' : '○──○'}
            </span>
          )}
        </Fragment>
      ))}
    </div>
  )
}
```

---

## 10. Edge Cases & Error Handling

### 10.1 Semua sub-agent gagal (Execute)

```
Semua 4 agent → ERROR
Validate → deteksi 4 anomaly → re-spawn 2x → semua masih gagal
Synthesis → generate report partial dengan catatan "semua agent gagal"
```

### 10.2 Sub-agent timeout

```
Execute → agent timeout → ErrorResponse
Validate → deteksi timeout → re-spawn dengan timeout 2x lipat
  - Re-spawn 1: timeout lagi → re-spawn 2
  - Re-spawn 2: timeout lagi → tandai failed permanent
```

### 10.3 Validate LLM decision override

```
Validate → orchestrator deteksi data valid
LLM boleh override: "Data terlihat valid, tapi confidence rendah. Re-spawn confirm."
→ Re-spawn 1x untuk confirm
```

### 10.4 Chain pendek (simple prompt)

```
User: "Halo"
Planning → chat mode → DONE (no phase chain)

User: "Apa itu audit lingkungan?"
Planning → LLM narrative → DONE (no Execute, no Validate)
```

---

## 11. Backward Compatibility

| Existing flow | 4-Fase impact |
|--------------|---------------|
| Chat mode (greeting) | Unchanged — langsung DONE |
| Simple audit (1 agent) | Execute 1 agent → Validate → Synthesis |
| Complex audit (4 agent) | Full 4-fase chain |
| `/api/telemetry` (GET) | Unchanged — existing SSE consumers |
| `/api/stream` (POST) | Enhanced — tambah phase metadata di events |
| Autonomous tasks (worker) | Unchanged — `worker.py` tidak disentuh |

---

## 12. Test Plan

### 12.1 Unit Tests (Backend)

| Test | Scope |
|------|-------|
| `test_phase_planning_emits_correct_metadata()` | Planning events punya `phase: planning` |
| `test_phase_execute_progress_events()` | Execute emits progress THINKING per agent |
| `test_phase_validate_no_anomaly()` | Validate dengan data valid → skip re-spawn |
| `test_phase_validate_with_anomaly()` | Validate deteksi anomaly → re-spawn |
| `test_phase_validate_max_re_spawn()` | Re-spawn gagal 2x → partial continue |
| `test_phase_synthesis_gets_full_context()` | Synthesis input includes all phase outputs |
| `test_context_propagation()` | Chain context passed correctly between phases |

### 12.2 Integration Tests

| Test | Scope |
|------|-------|
| `test_full_4_phase_pipeline()` | Planning → Execute → Validate → Synthesis → Done |
| `test_pipeline_with_re_spawn()` | Full pipeline dengan 1 agent re-spawn |
| `test_pipeline_all_failed()` | Semua agent gagal → partial report |
| `test_chat_mode_still_works()` | Greeting → skip pipeline → DONE |

---

## 13. Implementation Order

| # | Task | File | Priority |
|---|------|------|----------|
| 1 | Tambah `context_chain` dict di `run()` | orchestrator.py | High |
| 2 | Modifikasi Planning event + phase metadata | orchestrator.py | High |
| 3 | Modifikasi Execute: SPAWNING → THINKING + progress | orchestrator.py | High |
| 4 | Implementasi `_phase_validate()` | orchestrator.py | High |
| 5 | Enhanced synthesis input (context propagation) | orchestrator.py | High |
| 6 | Modifikasi Synthesis + DONE event phase metadata | orchestrator.py | High |
| 7 | Frontend: SSE event grouper by node_id | dashboard/page.tsx | High |
| 8 | Frontend: ManagerCompoundCard component | dashboard/page.tsx | High |
| 9 | Frontend: SubAgentGrid + SubAgentCard | dashboard/page.tsx | High |
| 10 | Frontend: PhaseChain component | dashboard/page.tsx | Medium |
| 11 | Frontend: ProgressBar component | dashboard/page.tsx | Medium |
| 12 | Frontend: AnimatePresence transitions | dashboard/page.tsx | Low |
| 13 | Tests: unit + integration | tests/ | Medium |
| 14 | Anti-halusinasi prompt (deferred) | orchestrator.py | Low |

---

## 14. Quick Reference

| Konsep | Singkatnya |
|--------|-----------|
| **4 fase** | Planning → Execute → Validate → Synthesis → Done |
| **Re-spawn** | Validate deteksi anomaly → spawn ulang agent spesifik → max 2x |
| **Phase chain** | Horizontal, grow ke kanan: `●──○──○──○` |
| **Sub-agent cards** | Grid horizontal di bawah Manager, persist |
| **THINKING display** | Latest only, replace previous, fade morph 400ms |
| **Context propagation** | Tiap fase terima output semua fase sebelumnya |
| **LLM calls** | 2x: Planning (`create_audit_plan`) + Synthesis (`generate_report`) |
| **NodeState** | No new enum. THINKING differentiated via `metadata.phase` |
| **SSE unchanged** | Same `event: state\n\ndata: {json}\n\n` format |
| **Backward compat** | Chat mode, `/api/telemetry`, worker — semua unchanged |

---

*Last updated: 15 Mei 2026 10:00 WITA*
*Ready for implementation*
