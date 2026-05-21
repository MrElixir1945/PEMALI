# PEMALI — Work Map

> Dibuat: 14 Mei 2026
> Status: Sprint 3 (Narrative + SDUI + Telemetry) — in progress

---

## Legend

| Mark | Meaning |
|------|---------|
| ✅ | Done, tested |
| ⌛ | Spec clear, ready to implement |
| 🎨 | Design phase |
| ⏳ | Needs discussion |
| 📋 | Backlog |

---

## 1. ✅ Done

### Core SSE Streaming
| # | Item | File | Status |
|---|------|------|--------|
| 1.1 | Direct backend SSE (no Next.js proxy buffer) | `frontend/.env.local`, `dashboard/page.tsx` | ✅ |
| 1.2 | Named SSE events (`event: state`, `event: token`) | `backend/core/orchestrator.py` | ✅ |
| 1.3 | Token-level LLM streaming to frontend | `backend/core/orchestrator.py` | ✅ |
| 1.4 | Manager function calling (`create_audit_plan` tool) | `backend/core/orchestrator.py` | ✅ |
| 1.5 | SubAgent function calling (`tool_choice: auto`) | `backend/core/orchestrator.py` | ✅ |
| 1.6 | Synthesis streaming + LLM narration | `backend/core/orchestrator.py` | ✅ |
| 1.7 | CORS middleware `*` | `backend/main.py` | ✅ |

### Agent Prompts
| # | Item | File | Status |
|---|------|------|--------|
| 2.1 | Manager NARRATIVE CONTRACT (replaced "JSON murni") | `backend/core/orchestrator.py` | ✅ |
| 2.2 | Manager GATE LOGIC (detect greeting vs audit) | `backend/core/orchestrator.py` | ✅ |
| 2.3 | Manager chat mode (no spawn for greetings) | `backend/core/orchestrator.py` | ✅ |
| 2.4 | Dynamic Tool Context (auto-inject tool list) | `backend/core/orchestrator.py` | ✅ |
| 2.5 | SubAgent ATURAN EKSEKUSI rewrite (narasi → tool call) | `backend/core/orchestrator.py` | ✅ |
| 2.6 | SubAgent ATURAN NARASI (natural, no raw JSON) | `backend/core/orchestrator.py` | ✅ |
| 2.7 | `get_scoped_manifests()` fallback (empty → all tools) | `backend/core/orchestrator.py` | ✅ |

### Frontend
| # | Item | File | Status |
|---|------|------|--------|
| 3.1 | Dashboard 60/40 layout (Observation / Interaction) | `frontend/src/app/dashboard/page.tsx` | ✅ |
| 3.2 | DAGCanvas (dagre layout + SVG edges) | `frontend/src/app/dashboard/page.tsx` | ✅ |
| 3.3 | SSE parser (event: state + event: token) | `frontend/src/app/dashboard/page.tsx` | ✅ |
| 3.4 | Live token display (typing effect) | `frontend/src/app/dashboard/page.tsx` | ✅ |
| 3.5 | ModuleOutput (final report markdown render) | `frontend/src/app/dashboard/page.tsx` | ✅ |
| 3.6 | NarrativeCard timeline | `frontend/src/app/dashboard/page.tsx` | ✅ |
| 3.7 | Zustand store (events + tokens + isStreaming) | `frontend/src/app/dashboard/page.tsx` | ✅ |
| 3.8 | Chat Input + send button | `frontend/src/app/dashboard/page.tsx` | ✅ |
| 3.9 | Sidebar session list | `frontend/src/app/dashboard/page.tsx` | ✅ |
| 3.10 | StatusBar (model + worker + event count) | `frontend/src/app/dashboard/page.tsx` | ✅ |
| 3.11 | Direct backend URL (${NEXT_PUBLIC_BACKEND_URL}) | `frontend/.env.local` | ✅ |
| 3.12 | `shortId()` guard for undefined node_id | `frontend/src/app/dashboard/page.tsx` | ✅ |

### Backend Infrastructure
| # | Item | File | Status |
|---|------|------|--------|
| 4.1 | LLM client (`get_llm_client()` singleton) | `backend/core/llm_client.py` | ✅ |
| 4.2 | `openai.AsyncOpenAI` SDK (replaced httpx) | `backend/core/llm_client.py` | ✅ |
| 4.3 | Telemetry proxy via contextvar | `backend/core/orchestrator.py` | ✅ |
| 4.4 | Error handling (APIError, APIConnectionError) | `backend/core/orchestrator.py` | ✅ |
| 4.5 | Self-correction retry (3x max) | `backend/core/orchestrator.py` | ✅ |
| 4.6 | `build_tool_context()` auto-generate tool docs | `backend/core/orchestrator.py` | ✅ |
| 4.7 | All tests pass (48/48) | `backend/tests/` | ✅ |

---

## 2. ⌛ Ready to Implement (spec clear)

### Anti-Halusinasi Prompt (Medium-Hard)
| # | Item | File |
|---|------|------|
| 5.1 | Tambah ATURAN KETERBATASAN di SubAgent prompt | `backend/core/orchestrator.py` |
| 5.2 | "JANGAN mengarang data. Bilang jujur jika tidak punya." | `backend/core/orchestrator.py` |
| 5.3 | "Nama lokasi/sungai spesifik HANYA dari tool output" | `backend/core/orchestrator.py` |
| 5.4 | "Data dari mock_data_generator adalah SIMULASI" | `backend/core/orchestrator.py` |

---

## 3. 🎨 UI Design Phase

### Morphing Card (Manager Stage Display)
| # | Item | Status |
|---|------|--------|
| 6.1 | Card type: persistent (1 card per agent) | 🎨 |
| 6.2 | Stage transition: fade morph (Framer Motion `AnimatePresence`) | 🎨 |
| 6.3 | Auto-expand current stage, user can collapse/close | 🎨 |
| 6.4 | Sub-agents as separate cards below Manager | 🎨 |
| 6.5 | Card height: fluid (adjust to content) | 🎨 |
| 6.6 | Progress indicator: bottom-left `●──○──○` style | 🎨 |
| 6.7 | Framer Motion specs (duration, easing) — deferred to polish | 🎨 |
| 6.8 | Backward compatible: current flow for simple requests | 🎨 |

### Stage Architecture
| # | Item | Decision |
|---|------|----------|
| 7.1 | Stage definition: Hybrid | ✅ Confirmed |
| 7.2 | Single Manager agent, dynamic stages (2-10+) | ✅ Confirmed |
| 7.3 | Stage determination: base hardcoded + LLM can insert/remove | ✅ Confirmed |

---

## 4. ⏳ Needs Discussion

### Loop Condition + Baseline
| # | Item | Options |
|---|------|---------|
| 8.1 | Loop trigger: data completeness | threshold: ? (e.g. <70%) |
| 8.2 | Loop trigger: confidence score | threshold: ? (e.g. <60%) |
| 8.3 | Loop trigger: anomaly count | threshold: ? (e.g. >3 anomalies) |
| 8.4 | Max iterations | cap: ? (e.g. 3) |
| 8.5 | LLM veto power over baseline? | Ya / Tidak |
| 8.6 | Stop condition logic | Agent decides with baseline guard |

### Multi-Stage Trigger
| # | Item | Options |
|---|------|---------|
| 9.1 | When to use multi-stage vs single-stage? | Keywords / LLM classifier / User choice / Always |
| 9.2 | Simple requests ("hai") → single-stage, skip pipeline | ✅ |

### DAG Render Options
| # | Item | Options |
|---|------|---------|
| 10.1 | How to render loop/iteration in DAG? | A: Flat / B: Counter / C: Animated / D: Tree |
| 10.2 | Edge deduplication for same tool calls | Needed? |
| 10.3 | Module node grouping (1 node vs per-call) | Current: 1 node per tool |

---

## 5. 📋 Backlog (Post-MVP)

### Tools & Modules
| # | Item | Priority |
|---|------|----------|
| 11.1 | Real modules (satellite_analysis, water_quality, web_scraper, etc.) | Medium |
| 11.2 | `agent_scope` field in module manifest (auto-scoping) | Low |
| 11.3 | Tool naming conventions (descriptive, not generic) | Low |

### Error Recovery
| # | Item | Priority |
|---|------|----------|
| 12.1 | Circuit breaker (stop on repeated 5xx from OpenRouter) | Medium |
| 12.2 | Dead letter queue (save failed tasks for later retry) | Medium |
| 12.3 | Alert/notification on repeated failures | Low |

### Memory & RAG
| # | Item | Priority |
|---|------|----------|
| 13.1 | Memory/RAG integration into agent narrative | Medium |
| 13.2 | Historical trend comparison in synthesis | Low |

### Polish
| # | Item | Priority |
|---|------|----------|
| 14.1 | Framer Motion transitions (duration, easing) | Low |
| 14.2 | Final report format (bilingual, PDF, chart render) | Low |
| 14.3 | Frontend polish (responsive, dark mode, accessibility) | Low |
| 14.4 | React key warning cleanup (duplicate node_id guard) | Low |

---

## Next Actions (ordered)

1. 🔴 **Anti-halusinasi prompt** (#5.1-5.4)
2. 🔴 **Loop condition + baseline discussion** (#8)
3. 🟡 **UI implementation** — morphing card, progress indicator (#6)
4. 🟡 **Multi-stage trigger decision** (#9)
5. 🟡 **DAG render decision** (#10)
6. 🟢 **Backlog items** (#11-14)

---

*Last updated: 14 Mei 2026 20:00 WITA*
