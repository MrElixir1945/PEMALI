# Draft: Frontend Refactor — Observation Zone Node-Based Visualization

> **Status:** IN PROGRESS  
> **Terakhir Diupdate:** 2026-05-11

---

## Layout Architecture

```
┌─ Navbar (top, full width) ──────────────────────────────────────────────┐
│  PEMALI | Model: deepseek-v4 | Worker: active | Last tick: 12:34:56   │
├──────────────────────┬──────────────────────────────────────────────────┤
│                      │                                                  │
│  Sidebar (hidden/    │  Main Content Area                               │
│  collapsible)        │  ┌──────────────────────────────┬──────────────┐ │
│                      │  │  Observation Zone (60%)      │ Interaction  │ │
│  • Chat history      │  │                              │ Zone (40%)   │ │
│  • Session list      │  │  ┌─ DAG Canvas ────────────┐ │              │ │
│  • New chat button   │  │  │  [dot grid bg]          │ │  Chat msgs   │ │
│                      │  │  │                          │ │  + input     │ │
│                      │  │  │  [Manager]──THINKING     │ │              │ │
│                      │  │  │     ├─[geo_agent]─DONE   │ │              │ │
│                      │  │  │     └─[water_agent]─EXEC │ │              │ │
│                      │  │  │          └─[water_qual]  │ │              │ │
│                      │  │  │                          │ │              │ │
│                      │  │  ├─ Node Detail Panel ─────┤ │              │ │
│                      │  │  │  (click node → detail)  │ │              │ │
│                      │  │  └──────────────────────────┘ │              │ │
│                      │  │                              │              │ │
│                      │  │  ┌─ SDUI Output ───────────┐ │              │ │
│                      │  │  │  map / table / chart     │ │              │ │
│                      │  │  └──────────────────────────┘ │              │ │
│                      │  └──────────────────────────────┴──────────────┘ │
└──────────────────────┴──────────────────────────────────────────────────┘
```

---

## Observation Zone — DAG Canvas

### Auto-Layout: Dagre
- Library: `dagre` (lightweight, 15KB gzipped)
- Algoritma: Hierarchical directed graph layout
- Cocok untuk PEMALI karena struktur Manager → SubAgent → Tool adalah tree-like DAG
- Node positioning otomatis berdasarkan parent-child relationships

### Grid Background
- CSS dot grid pattern (zero dependency)
- `radial-gradient(circle, rgba(255,255,255,0.05) 1px, transparent 1px)`
- Background-size: 24px 24px

### Node Design
Setiap node merepresentasikan agent/sub-agent/tool dengan:
- **Nama node** — e.g. "Manager", "geo_agent", "geo_sensor"
- **State badge** — THINKING (purple), SPAWNING (blue), EXECUTING (green), DONE (light green), ERROR (red)
- **Narrative text** — narasi singkat dari SSE event, e.g. "Menganalisis instruksi..."
- **Tipe indicator** — Manager / SubAgent / Module

### Node Interaction
- **Click** → Buka NodeDetailPanel di bawah canvas
- Detail panel show: full narrative, metadata (tool_name, duration_ms), state history

### Edges
- Garis panah dari parent ke child
- Warna berubah sesuai state parent node
- Animated dash saat EXECUTING

---

## Interaction Zone — Chat

### Desain: Terminal-Inspired Message List
- Bukan bubble chat SaaS biasa
- Monospace font untuk code/output
- Clean text untuk narasi
- Sesuai "Anthropic Terminal" aesthetic dari AGENTS.md

### Flow
1. User input prompt → POST /api/trigger
2. Input cleared, message muncul di chat
3. SSE stream di Observation Zone handle visualisasi
4. Agent response muncul di chat setelah DONE

---

## Animasi (DRAFT — implementasi belakangan)

- **Node spawn**: pop-in scale animation (0→1) saat node baru muncul
- **State transition**: color morph saat state berubah
- **Edge animation**: dash flow animation saat EXECUTING
- **Node pulse**: subtle pulse saat THINKING
- **Slide-in**: new node slide dari atas

---

## Component File Plan

| File | Action | Deskripsi |
|------|--------|-----------|
| `globals.css` | Rewrite | PEMALI dark theme tokens, CSS dot grid |
| `layout.tsx` | Edit | Geist font, dark body |
| `components/pemali/DAGCanvas.tsx` | **New** | Dagre auto-layout, node rendering, edges |
| `components/pemali/AgentNode.tsx` | **New** | Individual node component |
| `components/pemali/NodeDetailPanel.tsx` | **New** | Detail panel on click |
| `dashboard/page.tsx` | **Rewrite** | 60/40 split, sidebar, navbar |
| `page.tsx` | Edit | Dark theme landing |

## Dependencies
- `dagre` + `@types/dagre` — auto-layout engine
- Existing: `zustand`, `framer-motion`, `lucide-react`, `react-leaflet`
