import json
import httpx
import asyncio
import os
import datetime
import time
import uuid
from typing import List, Dict, Any, Optional
from backend.core.memory import query_semantic, store_semantic_memory, insert_memory_graph
from backend.core.memory_processor import TemporalPatternExtractor, KnowledgeGraphBuilder
from backend.core.models import MasterPlan, TaskIntent, TelemetryEvent, NodeState, ErrorResponse
from backend.core.telemetry import telemetry
from backend.core.registry import registry
from dotenv import load_dotenv

load_dotenv("config/.env")

OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")

SCOPE_MAP = {
    "geo_agent": ["geo_*", "satellite_*", "mapping_*"],
    "water_agent": ["water_*", "hydrology_*"],
    "fire_agent": ["fire_*", "thermal_*"],
    "osint_agent": ["osint_*", "news_*", "scrape_*"],
}


def _match_tool_pattern(tool_name: str, pattern: str) -> bool:
    if pattern.endswith("_*"):
        return tool_name.startswith(pattern[:-1])
    return tool_name == pattern


def get_scoped_manifests(agent_type: str, all_manifests: List[Dict]) -> List[Dict]:
    allowed = SCOPE_MAP.get(agent_type, [])
    if not allowed:
        return all_manifests
    return [
        m for m in all_manifests
        if any(_match_tool_pattern(m["name"], p) for p in allowed)
    ]


async def execute_subagent_with_safety(sub_agent: "SubAgent", trace_id: str, timeout: int = 45) -> Dict:
    try:
        return await asyncio.wait_for(sub_agent.execute(), timeout=timeout)
    except asyncio.TimeoutError:
        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id,
            node_id=sub_agent.task.target_agent,
            node_type="SubAgent",
            state=NodeState.ERROR,
            narrative=f"Timeout ({timeout}s) saat menjalankan task: {sub_agent.task.intent}"
        ))
        return ErrorResponse(
            status="TOOL_EXECUTION_FAILED",
            step="timeout",
            error_code="SUB_AGENT_TIMEOUT",
            context={
                "agent": sub_agent.task.target_agent,
                "task_id": sub_agent.task.task_id,
                "intent": sub_agent.task.intent,
                "timeout_seconds": timeout,
                "recommendation": "Task terlalu kompleks atau LLM sedang lambat. Coba kurangi kompleksitas prompt."
            }
        ).model_dump()
    except Exception as e:
        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id,
            node_id=sub_agent.task.target_agent,
            node_type="SubAgent",
            state=NodeState.ERROR,
            narrative=f"Fatal exception: {str(e)}"
        ))
        return ErrorResponse(
            status="TOOL_EXECUTION_FAILED",
            step="unknown",
            error_code="SUB_AGENT_FATAL",
            context={
                "agent": sub_agent.task.target_agent,
                "task_id": sub_agent.task.task_id,
                "exception": str(e),
                "recommendation": "Periksa log backend untuk detail."
            }
        ).model_dump()


class SubAgent:
    def __init__(self, task: TaskIntent, session_id: str, tools: List[Dict], trace_id: str):
        self.task = task
        self.session_id = session_id
        self.trace_id = trace_id
        self.tools = tools
        self.headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
        self.max_retries = 3

    async def execute(self) -> Dict:
        await telemetry.emit(TelemetryEvent(
            trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
            state=NodeState.THINKING, narrative=f"Menganalisis instruksi: {self.task.intent}..."
        ))

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

        for attempt in range(self.max_retries):
            payload = {"model": OPENROUTER_MODEL, "messages": messages, "tools": self.tools, "tool_choice": "auto"}

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    res = await client.post(OPENROUTER_URL, headers=self.headers, json=payload)
                    res.raise_for_status()
                    ai_msg = res.json()['choices'][0]['message']

                    messages.append(ai_msg)

                    if ai_msg.get("tool_calls"):
                        await telemetry.emit(TelemetryEvent(
                            trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                            state=NodeState.EXECUTING, narrative=f"Eksekusi tools (Attempt {attempt+1}/{self.max_retries})..."
                        ))

                        tasks = []
                        json_errors = []
                        for tc in ai_msg["tool_calls"]:
                            t_name = tc["function"]["name"]
                            try:
                                t_args = json.loads(tc["function"]["arguments"])
                                if "shared_data" in self.task.parameters:
                                    t_args["_shared_context"] = self.task.parameters["shared_data"]
                                tasks.append(self._execute_tool(t_name, t_args, tc["id"]))
                            except json.JSONDecodeError as je:
                                json_errors.append({
                                    "tool_call_id": tc["id"],
                                    "tool_name": t_name,
                                    "output": {"status": 400, "error_msg": f"JSON Parse Error: {str(je)}. Please provide valid JSON."}
                                })

                        results = await asyncio.gather(*tasks) if tasks else []
                        results.extend(json_errors)

                        has_error = False
                        final_results = []

                        for res_data in results:
                            messages.append({
                                "role": "tool",
                                "tool_call_id": res_data["tool_call_id"],
                                "name": res_data["tool_name"],
                                "content": json.dumps(res_data["output"])
                            })

                            output_payload = res_data["output"].copy()
                            output_payload["tool_name"] = res_data["tool_name"]
                            final_results.append(output_payload)

                            if res_data["output"].get("status") in [400, 500]:
                                has_error = True

                        if has_error and attempt < self.max_retries - 1:
                            await telemetry.emit(TelemetryEvent(
                                trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                                state=NodeState.THINKING, narrative="Mendeteksi error modul/format. Melakukan self-correction..."
                            ))
                            continue

                        await telemetry.emit(TelemetryEvent(
                            trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                            state=NodeState.DONE, narrative="Sub-task selesai."
                        ))
                        return {"agent": self.task.target_agent, "results": final_results}

                    return {"agent": self.task.target_agent, "response": ai_msg.get("content")}

            except httpx.HTTPError as he:
                if attempt < self.max_retries - 1:
                    await telemetry.emit(TelemetryEvent(
                        trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                        state=NodeState.ERROR, narrative=f"Network Error: {str(he)}. Retrying in 3s (Attempt {attempt+1}/{self.max_retries})..."
                    ))
                    await asyncio.sleep(3)
                    continue
                else:
                    await telemetry.emit(TelemetryEvent(
                        trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                        state=NodeState.ERROR, narrative=f"HTTP Error setelah {self.max_retries}x retry: {str(he)}"
                    ))
                    return ErrorResponse(
                        status="TOOL_EXECUTION_FAILED",
                        step="http_request",
                        error_code=f"OPENROUTER_HTTP_{getattr(he, 'response', None) and he.response.status_code or 'UNKNOWN'}",
                        context={
                            "agent": self.task.target_agent,
                            "task_id": self.task.task_id,
                            "attempts_made": self.max_retries,
                            "last_error": str(he),
                            "recommendation": "Coba lagi nanti atau periksa status OpenRouter API."
                        }
                    ).model_dump()

            except Exception as e:
                await telemetry.emit(TelemetryEvent(
                    trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                    state=NodeState.ERROR, narrative=f"Fatal Error: {str(e)}"
                ))
                return ErrorResponse(
                    status="TOOL_EXECUTION_FAILED",
                    step="unknown",
                    error_code="SUB_AGENT_UNEXPECTED",
                    context={
                        "agent": self.task.target_agent,
                        "task_id": self.task.task_id,
                        "exception": str(e),
                        "recommendation": "Periksa log backend untuk detail lengkap."
                    }
                ).model_dump()

        return ErrorResponse(
            status="TOOL_EXECUTION_FAILED",
            step="max_retries",
            error_code="MAX_RETRIES_REACHED",
            context={
                "agent": self.task.target_agent,
                "task_id": self.task.task_id,
                "attempts_made": self.max_retries,
                "recommendation": "LLM tidak berhasil menyelesaikan task setelah retry maksimal. Periksa apakah tools tersedia dan parameter valid."
            }
        ).model_dump()

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


class PemaliOrchestrator:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}

    def _is_error_response(self, res: Dict) -> bool:
        return isinstance(res, dict) and res.get("status") in [
            "TOOL_EXECUTION_FAILED", "VALIDATION_ERROR", "TIMEOUT"
        ]

    async def run(self, prompt: str):
        trace_id = f"tr-{uuid.uuid4().hex[:16]}"

        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="manager", node_type="Manager",
            state=NodeState.THINKING, narrative="Menyusun Master Plan berbasis RAG..."
        ))

        past_memories = await asyncio.to_thread(query_semantic, prompt, 2)
        rag_context = "\n".join([f"- {m['content']}" for m in past_memories]) if past_memories else ""

        # RAG context
        rag_part = f"\n# KONTEKS HISTORIS\n{rag_context}\n" if rag_context else ""

        sys_prompt = (
            "Kamu adalah MANAGER AGENT dalam sistem audit lingkungan Bali.\n"
            "Tugas: analisis permintaan user, buat rencana kerja dalam JSON.\n\n"
            "Output HARUS berupa JSON murni, tanpa markdown, tanpa teks lain:\n"
            '{"trace_id": "string", "tasks": [{"task_id": "string", "target_agent": "string", "intent": "string", "depends_on": ["task_id"]}]}\n\n'
            "target_agent pilih dari: geo_agent, water_agent, fire_agent, osint_agent, scheduler_agent\n"
            f"Gunakan depends_on untuk urutan — task yang tidak punya dependency jalan paralel.{rag_part}"
        )

        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }

        # Retry up to 2x untuk plan generation
        plan = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    res = await client.post(OPENROUTER_URL, headers=self.headers, json=payload)
                    res.raise_for_status()
                    plan_raw = res.json()['choices'][0]['message']['content']
                plan = MasterPlan(**json.loads(plan_raw))
                plan.trace_id = trace_id
                break
            except Exception as e:
                if attempt < 2:
                    await telemetry.emit(TelemetryEvent(
                        trace_id=trace_id, node_id="manager", node_type="Manager",
                        state=NodeState.ERROR, narrative=f"Plan retry {attempt+1}: {str(e)[:80]}"
                    ))
                    await asyncio.sleep(1)
                else:
                    await telemetry.emit(TelemetryEvent(
                        trace_id=trace_id, node_id="manager", node_type="Manager",
                        state=NodeState.ERROR, narrative=f"Plan Error setelah 3x percobaan: {e}"
                    ))
                    return f"Error: Gagal menyusun rencana setelah 3x percobaan."

        if not plan:
            return "Error: Gagal menyusun rencana."

        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="manager", node_type="Manager",
            state=NodeState.SPAWNING, narrative=f"Menjalankan {len(plan.tasks)} tugas dalam urutan DAG..."
        ))

        all_manifests = registry.get_all_manifests()

        shared_context = {}
        completed_tasks = set()
        failed_tasks = {}
        pending_tasks = {t.task_id: t for t in plan.tasks}

        while pending_tasks:
            ready_tasks = [
                t for t in pending_tasks.values()
                if all(dep in completed_tasks for dep in t.depends_on)
            ]

            if not ready_tasks:
                raise ValueError("DAG Deadlock terdeteksi: Circular dependency.")

            for t in ready_tasks:
                if t.depends_on:
                    t.parameters["shared_data"] = {
                        d: shared_context.get(d, {"_DAG_INCOMPLETE_": f"Task '{d}' gagal atau tidak ada data."})
                        for d in t.depends_on
                    }

            coroutines = []
            for t in ready_tasks:
                scoped_manifests = get_scoped_manifests(t.target_agent, all_manifests)
                tools = [{"type": "function", "function": m} for m in scoped_manifests]
                sub = SubAgent(t, self.session_id, tools, trace_id)
                coroutines.append(execute_subagent_with_safety(sub, trace_id, timeout=45))

            results = await asyncio.gather(*coroutines, return_exceptions=True)

            for t, res in zip(ready_tasks, results):
                if isinstance(res, Exception):
                    failed_tasks[t.task_id] = {
                        "agent": t.target_agent,
                        "intent": t.intent,
                        "error": str(res),
                        "error_type": "unhandled_exception"
                    }
                    shared_context[t.task_id] = {
                        "_ERROR_": {
                            "agent": t.target_agent,
                            "intent": t.intent,
                            "status": "CRASH",
                            "detail": str(res)
                        }
                    }
                elif self._is_error_response(res):
                    failed_tasks[t.task_id] = {
                        "agent": t.target_agent,
                        "intent": t.intent,
                        "error": res.get("error_code", "UNKNOWN"),
                        "context": res.get("context", {}),
                        "error_type": "structured_error"
                    }
                    shared_context[t.task_id] = {
                        "_ERROR_": {
                            "agent": t.target_agent,
                            "intent": t.intent,
                            "status": res.get("error_code", "UNKNOWN"),
                            "detail": res.get("context", {}).get("recommendation", str(res))
                        }
                    }
                elif "response" in res:
                    shared_context[t.task_id] = {t.target_agent: res["response"]}
                else:
                    filtered_res = {}
                    for r in res.get("results", []):
                        tool_name = r.get("tool_name", "unknown")
                        clean_output = r.copy()
                        if "tool_name" in clean_output:
                            del clean_output["tool_name"]
                        filtered_res[tool_name] = clean_output
                    shared_context[t.task_id] = filtered_res

                completed_tasks.add(t.task_id)
                del pending_tasks[t.task_id]

        raw_results = list(shared_context.values())

        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="manager", node_type="Manager",
            state=NodeState.THINKING, narrative="Sintesis laporan final..."
        ))

        synth_input = {
            "successful_results": [r for r in raw_results if "_ERROR_" not in r],
            "failed_tasks": [{"task_id": tid, **info} for tid, info in failed_tasks.items()],
            "partial_data_warning": len(failed_tasks) > 0
        }

        synth_payload = {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": f"Synthesize these audit results into a comprehensive report. Include a section about any failed tasks if present:\n{json.dumps(synth_input)}"}],
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            res_synth = await client.post(OPENROUTER_URL, headers=self.headers, json=synth_payload)
            res_synth.raise_for_status()
            report = res_synth.json()['choices'][0]['message']['content']

        # Cognitive Memory: Extract temporal patterns and save to knowledge graph
        try:
            extractor = TemporalPatternExtractor()
            builder = KnowledgeGraphBuilder()

            # Prepare raw audit data (only successful results, not errors)
            raw_audit_data = {}
            for task_id, data in shared_context.items():
                if "_ERROR_" not in data and not any(k.startswith("_") for k in str(data)):
                    raw_audit_data[task_id] = data

            if raw_audit_data:
                # Extract snapshot
                snapshot = extractor.extract(raw_audit_data, session_id=trace_id)

                # Build nodes and edges
                nodes = builder.build_nodes(snapshot)

                # Map labels to IDs (memory_node_id in edges refers to label in simple mapping)
                label_to_id = {n["label"]: 0 for n in nodes}  # Placeholder, will be resolved by insert_memory_graph

                edges = builder.build_edges(snapshot, label_to_id)

                # Insert into knowledge graph
                graph_result = insert_memory_graph(trace_id, nodes, edges)

                await telemetry.emit(TelemetryEvent(
                    trace_id=trace_id, node_id="manager", node_type="Manager",
                    state=NodeState.THINKING, narrative=f"Cognitive Memory: {graph_result.get('nodes_created', 0)} nodes linked."
                ))
        except Exception as e:
            # Non-critical: don't crash if memory processing fails
            await telemetry.emit(TelemetryEvent(
                trace_id=trace_id, node_id="manager", node_type="Manager",
                state=NodeState.ERROR, narrative=f"Cognitive Memory extraction (non-critical): {str(e)[:100]}"
            ))

        await telemetry.emit(TelemetryEvent(trace_id=trace_id, node_id="manager", node_type="Manager", state=NodeState.DONE, narrative="Audit selesai."))

        await asyncio.to_thread(store_semantic_memory, self.session_id, f"Audit Result: {report}")
        return report