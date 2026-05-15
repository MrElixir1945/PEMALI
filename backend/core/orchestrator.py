import json
import asyncio
import os
import datetime
import time
import uuid
import logging
import contextvars
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI, APIError, APIConnectionError, APIStatusError
from backend.core.memory import query_semantic, query_memory_graph_for_context, store_semantic_memory, insert_memory_graph
from backend.core.memory_processor import TemporalPatternExtractor, KnowledgeGraphBuilder
from backend.core.models import MasterPlan, TaskIntent, TelemetryEvent, NodeState, ErrorResponse
from backend.core.telemetry import telemetry
from backend.core.registry import registry
from backend.core.llm_client import get_llm_client
from backend.core.session_logger import SessionLogger
from dotenv import load_dotenv

load_dotenv("config/.env")

logger = logging.getLogger("PEMALI.Orchestrator")

OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")

# Context variable untuk token streaming — dipakai SubAgent buat push token ke SSE stream
stream_queue_var: contextvars.ContextVar = contextvars.ContextVar('stream_queue', default=None)

# Manager plan tool — function calling instead of json_object
PLAN_TOOL = {
    "type": "function",
    "function": {
        "name": "create_audit_plan",
        "description": "Create a structured audit plan with task delegation for environmental auditing in Bali",
        "parameters": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string"},
                            "target_agent": {
                                "type": "string",
                                "enum": ["geo_agent", "water_agent", "fire_agent", "osint_agent", "scheduler_agent"]
                            },
                            "intent": {"type": "string"},
                            "depends_on": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of task_ids this task depends on. Empty array = run immediately."
                            }
                        },
                        "required": ["task_id", "target_agent", "intent", "depends_on"]
                    }
                }
            },
            "required": ["tasks"]
        }
    }
}

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
    filtered = [
        m for m in all_manifests
        if any(_match_tool_pattern(m["name"], p) for p in allowed)
    ]
    return filtered if filtered else all_manifests


def build_tool_context(manifests: List[Dict], agent_type: str | None = None) -> str:
    """Build auto-generated tool context string for system prompts."""
    if not manifests:
        return "\n# TOOLS\nTidak ada tools tersedia. Gunakan narasi natural saja.\n"
    label = f"untuk {agent_type}" if agent_type else "di sistem"
    lines = [f"\n# TOOLS YANG TERSEDIA ({label})"]
    lines.append(f"Total {len(manifests)} tool:")
    for m in manifests:
        # Handle both formats: flat {name, description, parameters} and nested {function: {name, ...}}
        fn = m.get("function", m)
        name = fn.get("name", "unknown")
        desc = fn.get("description", "no description")
        params_schema = fn.get("parameters", {}).get("properties", {})
        param_keys = list(params_schema.keys())
        lines.append(f"- `{name}`: {desc}")
        if param_keys:
            lines.append(f"  Parameter: {', '.join(param_keys)}")
    lines.append("\nGunakan function calling untuk memanggil tool yang ada.")
    lines.append("JANGAN memanggil tool yang tidak terdaftar di atas.")
    return "\n".join(lines)


async def execute_subagent_with_safety(sub_agent: "SubAgent", trace_id: str, timeout: int = 45) -> Dict:
    logger.debug(f"[SubAgent] Starting with safety wrapper: agent={sub_agent.task.target_agent}, timeout={timeout}s")
    try:
        result = await asyncio.wait_for(sub_agent.execute(), timeout=timeout)
        logger.debug(f"[SubAgent] Completed successfully")
        return result
    except asyncio.TimeoutError:
        logger.error(f"[SubAgent] Timeout after {timeout}s for agent {sub_agent.task.target_agent}")
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
        logger.error(f"[SubAgent] Fatal exception: {e}", exc_info=True)
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

    async def _call_llm_streaming(self, messages: List[Dict]) -> Dict:
        """Stream LLM response via openai SDK. Push tokens to stream_queue contextvar."""
        stream_queue = stream_queue_var.get()
        logger.debug(f"[SubAgent._call_llm_streaming] stream_queue={stream_queue is not None}, node_id={self.task.target_agent}")
        llm = get_llm_client()

        full_content = ""
        tool_call_accum: Dict[int, Dict] = {}

        stream = await llm.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages,
            tools=self.tools if self.tools else None,
            tool_choice="auto" if self.tools else None,
            stream=True,
            timeout=180.0,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            if delta.content:
                full_content += delta.content
                if stream_queue is not None:
                    await stream_queue.put({
                        "_sse_event": "token",
                        "node_id": self.task.target_agent,
                        "content": delta.content
                    })
                    logger.debug(f"[SubAgent] Token pushed: {len(delta.content)} chars")

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index if hasattr(tc, 'index') else 0
                    if idx not in tool_call_accum:
                        tool_call_accum[idx] = {
                            'id': '', 'type': 'function',
                            'function': {'name': '', 'arguments': ''}
                        }
                    acc = tool_call_accum[idx]
                    if tc.id: acc['id'] = tc.id
                    fn = tc.function
                    if fn and fn.name: acc['function']['name'] += fn.name
                    if fn and fn.arguments: acc['function']['arguments'] += fn.arguments

        result = {"content": full_content}
        if tool_call_accum:
            result["tool_calls"] = list(tool_call_accum.values())
        return result

    async def execute(self) -> Dict:
        logger.info(f"[SubAgent] Starting execution: agent={self.task.target_agent}, task_id={self.task.task_id}")
        scoped_context = build_tool_context(self.tools, self.task.target_agent)

        system_prompt = (
            "[PEMALI NARRATIVE CONTRACT v1]\n"
            f"Anda adalah {self.task.target_agent}, spesialis dalam audit lingkungan Bali.\n"
            f"Tugas spesifik Anda: {self.task.intent}\n\n"

            f"{scoped_context}\n\n"

            "# ATURAN EKSEKUSI (prioritas #1)\n"
            "1. Analisa task — pahami intent user\n"
            "2. Narasikan pendekatanmu dalam 1-2 kalimat bahasa Indonesia natural\n"
            "3. Panggil tool yang relevan dari daftar # TOOLS — sistem akan otomatis eksekusi\n"
            "4. Setelah hasil tool masuk, interpretasikan data dalam narasi ringkas\n\n"

            "# ATURAN NARASI\n"
            "Narasi harus natural, bukan JSON mentah.\n"
            "Ceritakan apa yang KAMU LAKUKAN dan TEMUAN yang didapat.\n"
            "JANGAN output JSON — JSON hanya untuk function calling, bukan untuk narasi.\n"
            "Narasi dalam bahasa Indonesia natural, ringkas, informatif.\n\n"

            "# ATURAN KOREKSI DIRI\n"
            "Jika tool gagal (status 4xx/5xx), baca pesan error, sesuaikan parameter, dan coba lagi.\n"
            "Maksimal 3x percobaan per tool.\n\n"

            "# ATURAN TEKNIS\n"
            f"Gunakan function-calling JSON standard. Shared data tersedia di parameters jika ada.\n\n"

            "# KRITIKAL\n"
            "Tool yang bisa kamu panggil HANYA yang terdaftar di # TOOLS di atas.\n"
            "Jangan hallucinate tool yang tidak ada.\n"
            "Kalau tidak ada tools, narasikan saja — jangan paksa bikin JSON."
        )

        messages = [{"role": "system", "content": system_prompt}]

        for attempt in range(self.max_retries):
            payload = {"model": OPENROUTER_MODEL, "messages": messages, "tools": self.tools, "tool_choice": "auto"}

            try:
                stream_queue = stream_queue_var.get()
                if stream_queue is not None:
                    logger.info(f"[SubAgent] Streaming LLM (attempt {attempt+1}/{self.max_retries})")
                    ai_msg = await self._call_llm_streaming(messages)
                    logger.info(f"[SubAgent] Stream complete: {len(ai_msg.get('content',''))} chars")
                else:
                    logger.info(f"[SubAgent] Calling LLM non-streaming (attempt {attempt+1}/{self.max_retries})")
                    llm = get_llm_client()
                    res = await llm.chat.completions.create(
                        model=OPENROUTER_MODEL,
                        messages=messages,
                        tools=self.tools if self.tools else None,
                        tool_choice="auto" if self.tools else None,
                        timeout=60.0,
                    )
                    ai_msg_raw = res.choices[0].message
                    ai_msg = {"role": "assistant", "content": ai_msg_raw.content or ""}
                    if hasattr(ai_msg_raw, 'tool_calls') and ai_msg_raw.tool_calls:
                        ai_msg["tool_calls"] = [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in ai_msg_raw.tool_calls
                        ]

                llm_narrative = ai_msg.get("content") or ""
                logger.critical(f"[SubAgent] === LLM RESPONSE [{self.task.target_agent}] ===")
                logger.critical(f"[SubAgent] Narrative: {llm_narrative[:500]}")
                if ai_msg.get("tool_calls"):
                    for tc in ai_msg["tool_calls"]:
                        logger.critical(f"[SubAgent] Tool Call: {tc['function']['name']}")
                        logger.critical(f"[SubAgent] Args: {tc['function']['arguments'][:500]}")
                else:
                    logger.critical(f"[SubAgent] No tool calls - pure text response")
                logger.critical(f"[SubAgent] === END RESPONSE ===")

                await telemetry.emit(TelemetryEvent(
                    trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                    state=NodeState.THINKING, narrative=llm_narrative or f"Menganalisis instruksi: {self.task.intent}..."
                ))

                messages.append(ai_msg)

                if ai_msg.get("tool_calls"):
                    tool_names = [tc["function"]["name"] for tc in ai_msg["tool_calls"]]
                    logger.info(f"[SubAgent] Executing tools: {tool_names}")
                    await telemetry.emit(TelemetryEvent(
                        trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                        state=NodeState.EXECUTING, narrative=f"Menjalankan: {', '.join(tool_names)}"
                    ))

                    tasks = []
                    json_errors = []
                    for tc in ai_msg["tool_calls"]:
                        t_name = tc["function"]["name"]
                        try:
                            t_args = json.loads(tc["function"]["arguments"])
                            logger.debug(f"[SubAgent] Tool call: {t_name}, args={t_args}")
                            if "shared_data" in self.task.parameters:
                                t_args["_shared_context"] = self.task.parameters["shared_data"]
                            tasks.append(self._execute_tool(t_name, t_args, tc["id"]))
                        except json.JSONDecodeError as je:
                            logger.error(f"[SubAgent] JSON decode error for tool {t_name}: {je}")
                            json_errors.append({
                                "tool_call_id": tc["id"],
                                "tool_name": t_name,
                                "output": {"status": 400, "error_msg": f"JSON Parse Error: {str(je)}. Please provide valid JSON."}
                            })

                    logger.debug(f"[SubAgent] Gathering {len(tasks)} tool results")
                    results = await asyncio.gather(*tasks) if tasks else []
                    results.extend(json_errors)

                    logger.critical(f"[SubAgent] === TOOL RESULTS [{self.task.target_agent}] ===")
                    for r in results:
                        logger.critical(f"[SubAgent] Tool: {r['tool_name']}")
                        logger.critical(f"[SubAgent] Output: {json.dumps(r['output'])[:500]}")
                    logger.critical(f"[SubAgent] === END TOOL RESULTS ===")

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
                            logger.warning(f"[SubAgent] Tool {res_data['tool_name']} returned error status: {res_data['output'].get('status')}")
                            has_error = True

                    if has_error and attempt < self.max_retries - 1:
                        logger.info(f"[SubAgent] Tool error detected, retrying (attempt {attempt+2}/{self.max_retries})")
                        await telemetry.emit(TelemetryEvent(
                            trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                            state=NodeState.THINKING, narrative=f"Tool error detected. Retrying (attempt {attempt+2}/{self.max_retries})..."
                        ))
                        continue

                    if has_error:
                        logger.warning(f"[SubAgent] {self.task.target_agent} failed on last attempt — all retries exhausted.")
                        await telemetry.emit(TelemetryEvent(
                            trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                            state=NodeState.ERROR, narrative=f"Gagal setelah {self.max_retries}x percobaan: tool error bertahan."
                        ))
                    else:
                        await telemetry.emit(TelemetryEvent(
                            trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                            state=NodeState.DONE, narrative=llm_narrative or "Sub-task selesai."
                        ))
                    return {"agent": self.task.target_agent, "results": final_results}

                await telemetry.emit(TelemetryEvent(
                    trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                    state=NodeState.DONE, narrative=ai_msg.get("content") or "Sub-task selesai."
                ))
                return {"agent": self.task.target_agent, "response": ai_msg.get("content")}

            except (APIError, APIConnectionError, APIStatusError) as oe:
                if attempt < self.max_retries - 1:
                    await telemetry.emit(TelemetryEvent(
                        trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                        state=NodeState.ERROR, narrative=f"LLM Error: {str(oe)[:100]}. Retrying in 3s (Attempt {attempt+1}/{self.max_retries})..."
                    ))
                    await asyncio.sleep(3)
                    continue
                else:
                    await telemetry.emit(TelemetryEvent(
                        trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                        state=NodeState.ERROR, narrative=f"LLM Error setelah {self.max_retries}x retry: {str(oe)[:100]}"
                    ))
                    return ErrorResponse(
                        status="TOOL_EXECUTION_FAILED",
                        step="http_request",
                        error_code=f"OPENROUTER_API_ERROR",
                        context={
                            "agent": self.task.target_agent,
                            "task_id": self.task.task_id,
                            "attempts_made": self.max_retries,
                            "last_error": str(oe)[:200],
                            "recommendation": "Coba lagi nanti atau periksa status OpenRouter API."
                        }
                    ).model_dump()

            except Exception as e:
                logger.error(f"[SubAgent] Unexpected error: {e}", exc_info=True)
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
        logger.debug(f"[Module] Executing: {name}, args={args}")

        await telemetry.emit(TelemetryEvent(
            trace_id=self.trace_id, node_id=name, node_type="Module",
            state=NodeState.EXECUTING, narrative=f"Menjalankan modul [{name}]...",
            metadata={"tool_name": name, "phase": "start"}
        ))
        try:
            output = await registry.execute_tool(name, args, session_id=self.session_id)
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)
            logger.debug(f"[Module] {name} completed in {duration_ms}ms, status={output.status}")

            await telemetry.emit(TelemetryEvent(
                trace_id=self.trace_id, node_id=name, node_type="Module",
                state=NodeState.DONE, narrative=f"Modul [{name}] selesai.",
                metadata={"tool_name": name, "duration_ms": duration_ms, "status": output.status}
            ))

            return {"tool_call_id": tool_call_id, "tool_name": name, "output": output.model_dump()}
        except Exception as e:
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)
            logger.error(f"[Module] {name} failed: {e}")

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

    async def _phase_validate(self, shared_context: Dict, failed_tasks: Dict, 
                              plan: "MasterPlan", trace_id: str) -> tuple:
        """Fase 3: Validasi hasil agent, trigger re-spawn jika anomali.
        
        Returns: (shared_context, failed_tasks, re_spawn_log, validate_summary)
        """
        re_spawn_log = []
        max_re_spawn = 2
        validate_narratives = []

        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="manager", node_type="Manager",
            state=NodeState.THINKING,
            narrative=f"Memvalidasi data dari {len(shared_context)} agent...",
            metadata={"phase": "validate", "phase_step": "checking"}
        ))
        validate_narratives.append(f"Memvalidasi {len(shared_context)} agent.")

        anomalies = []
        for task_id, data in shared_context.items():
            if "_ERROR_" in data:
                err_info = data.get("_ERROR_", {})
                anomaly_agent = err_info.get("agent", task_id)
                anomalies.append((task_id, anomaly_agent, "error", data))
            elif not data or data == {} or "data not found" in str(data).lower():
                task_map = {t.task_id: t for t in plan.tasks}
                anomaly_agent = task_map.get(task_id, TaskIntent(task_id=task_id, target_agent=task_id, intent="")).target_agent
                anomalies.append((task_id, anomaly_agent, "empty", data))

        for task_id, agent, reason, data in anomalies:
            re_spawned_ok = False
            for attempt in range(1, max_re_spawn + 1):
                reason_text = "error" if reason == "error" else "data kosong"
                sp_narrative = f"Anomali di {agent}: {reason_text}. Re-spawn attempt {attempt}/{max_re_spawn}."
                await telemetry.emit(TelemetryEvent(
                    trace_id=trace_id, node_id="manager", node_type="Manager",
                    state=NodeState.THINKING, narrative=sp_narrative,
                    metadata={"phase": "validate", "phase_step": "anomaly",
                              "agent": agent, "reason": reason, "attempt": attempt}
                ))
                validate_narratives.append(sp_narrative)

                # Re-execute sub-agent
                all_manifests = registry.get_all_manifests()
                scoped = get_scoped_manifests(agent, all_manifests)
                tools = [{"type": "function", "function": m} for m in scoped]
                task = next((t for t in plan.tasks if t.task_id == task_id), None)
                if not task:
                    sub = TaskIntent(task_id=task_id, target_agent=agent, intent=f"Re-spawn untuk validasi {task_id}")
                else:
                    sub = task

                sub_agent = SubAgent(sub, self.session_id, tools, trace_id)
                result = await execute_subagent_with_safety(sub_agent, trace_id, timeout=45)

                if not self._is_error_response(result) and not (
                    isinstance(result, dict) and "_ERROR_" in result
                ):
                    shared_context[task_id] = result
                    failed_tasks.pop(task_id, None)
                    ok_narrative = f"Re-spawn {agent} sukses pada attempt {attempt}."
                    await telemetry.emit(TelemetryEvent(
                        trace_id=trace_id, node_id="manager", node_type="Manager",
                        state=NodeState.THINKING, narrative=ok_narrative,
                        metadata={"phase": "validate", "phase_step": "re-spawn-done",
                                  "agent": agent, "attempt": attempt, "status": "success"}
                    ))
                    validate_narratives.append(ok_narrative)
                    re_spawn_log.append({"agent": agent, "attempt": attempt, "status": "success", "reason": reason})
                    re_spawned_ok = True
                    break

            if not re_spawned_ok:
                fail_narrative = f"Re-spawn {agent} gagal setelah {max_re_spawn}x attempt. Lanjut dengan partial data."
                await telemetry.emit(TelemetryEvent(
                    trace_id=trace_id, node_id="manager", node_type="Manager",
                    state=NodeState.THINKING, narrative=fail_narrative,
                    metadata={"phase": "validate", "phase_step": "re-spawn-done",
                              "agent": agent, "attempt": max_re_spawn, "status": "failed"}
                ))
                validate_narratives.append(fail_narrative)
                re_spawn_log.append({"agent": agent, "attempt": max_re_spawn, "status": "failed", "reason": reason})

        success_count = len(shared_context) - len(failed_tasks)
        if anomalies:
            validate_summary = (
                f"Validasi: {success_count}/{len(shared_context)} agent sukses."
                f" {len(anomalies)} anomali terdeteksi, "
                f"{len([r for r in re_spawn_log if r['status'] == 'success'])} berhasil di-re-spawn."
            )
        else:
            validate_summary = f"Semua {success_count} agent valid tanpa anomali."

        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="manager", node_type="Manager",
            state=NodeState.THINKING, narrative=validate_summary,
            metadata={"phase": "validate", "phase_step": "valid"}
        ))
        validate_narratives.append(validate_summary)

        return shared_context, failed_tasks, re_spawn_log, validate_summary

    async def run_streaming(self, prompt: str):
        """Async generator — yields TelemetryEvent dicts for direct SSE streaming."""
        event_queue: asyncio.Queue = asyncio.Queue()
        original_emit = telemetry.emit
        ctx_token = stream_queue_var.set(event_queue)
        logger.debug(f"[run_streaming] context set, queue={id(event_queue)}")

        session_logger = SessionLogger("pending", self.session_id, prompt)

        async def proxy_emit(event: TelemetryEvent):
            data = event.model_dump(mode='json')
            data["_sse_event"] = "state"
            logger.debug(f"[run_streaming] Proxy emit: {event.node_id} - {event.state}")
            await event_queue.put(data)
            await original_emit(event)
            await asyncio.sleep(0)
            # Accumulate for session log
            session_logger.events.append(data)

        telemetry.emit = proxy_emit
        try:
            task = asyncio.create_task(self.run(prompt))
            while True:
                try:
                    data = await asyncio.wait_for(event_queue.get(), timeout=0.5)
                    event_name = data.pop("_sse_event", "state")
                    logger.debug(f"[run_streaming] Yield: {data.get('node_id')} - {data.get('state')}")
                    yield f"event: {event_name}\ndata: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    if task.done():
                        break
        finally:
            telemetry.emit = original_emit
            stream_queue_var.reset(ctx_token)
            # Update trace_id from first event, then write session log
            if session_logger.events:
                session_logger.trace_id = session_logger.events[0].get("trace_id", session_logger.trace_id)
            asyncio.create_task(asyncio.to_thread(session_logger.write))

    async def run(self, prompt: str):
        trace_id = f"tr-{uuid.uuid4().hex[:16]}"
        logger.critical(f"[Manager] >>>>> Starting run: trace_id={trace_id} <<<<<")
        logger.info(f"[Manager] Starting run: trace_id={trace_id}, prompt={prompt[:100]}...")

        self.context_chain = {
            "user_request": prompt,
            "plan": None,
            "plan_narrative": "",
            "execute_narrative": [],
            "raw_results": {},
            "validate_narrative": [],
            "validate_summary": "",
            "re_spawn_log": [],
        }

        logger.debug("[Manager] Querying RAG context (ChromaDB + Knowledge Graph)")
        try:
            past_memories, graph_context = await asyncio.gather(
                asyncio.to_thread(query_semantic, prompt, 2),
                asyncio.to_thread(query_memory_graph_for_context, prompt, 5, 5)
            )
            logger.debug(f"[Manager] RAG query completed")
        except Exception as e:
            logger.warning(f"[Manager] RAG query failed (continuing without): {e}")
            past_memories = []
            graph_context = ""
        rag_context = "\n".join([f"- {m['content']}" for m in past_memories]) if past_memories else ""
        logger.debug(f"[Manager] RAG context: {len(past_memories)} memories, graph_context={bool(graph_context)}")

        rag_part = f"\n# KONTEKS HISTORIS (ChromaDB)\n{rag_context}\n" if rag_context else ""
        graph_part = f"\n# KONTEKS KNOWLEDGE GRAPH (PostgreSQL)\n{graph_context}\n" if graph_context else ""

        all_manifests = registry.get_all_manifests()
        tool_context = build_tool_context(all_manifests)

        sys_prompt = (
            "[PEMALI NARRATIVE CONTRACT v1]\n"
            "Anda adalah MANAGER AGENT dalam sistem audit lingkungan Bali.\n"
            "Tugas Anda: analisis permintaan user, dekomposisi menjadi sub-tugas terstruktur, delegasikan ke Sub-Agent yang sesuai, lalu sintesis hasilnya.\n\n"

            f"{tool_context}\n\n"

            "# GATE LOGIC (evaluasi dulu sebelum bertindak)\n"
            "Apakah ini PERMINTAAN AUDIT LINGKUNGAN atau SEKADAR PERCAKAPAN BIASA?\n"
            "- Jika hanya salam, sapaan, tanya kabar, atau obrolan ringan → JAWAB LANGSUNG tanpa tool.\n"
            "- Jika user meminta data, investigasi, audit kawasan, analisis lingkungan, atau informasi spesifik Bali → gunakan tool create_audit_plan.\n"
            "Jangan spawn SubAgent untuk percakapan ringan — itu buang sumber daya.\n\n"

            "# ATURAN NARASI\n"
            "SEBELUM membuat plan, narasikan dulu dalam bahasa Indonesia:\n"
            "- Area audit apa yang kamu identifikasi dari permintaan user\n"
            "- Mengapa area tersebut prioritas untuk diaudit\n"
            "- Agent mana yang paling cocok dan mengapa\n"
            "Narasi akan ditampilkan ke user — ceritakan proses berpikirmu.\n\n"

            "# FORMAT OUTPUT\n"
            "Setelah narasi, gunakan tool create_audit_plan untuk output rencana terstruktur.\n"
            "Agent yang tersedia: geo_agent, water_agent, fire_agent, osint_agent, scheduler_agent\n"
            "depends_on untuk urutan DAG — task tanpa dependency dikerjakan paralel.\n"
            "PENTING: hanya assign task yang sesuai dengan tools yang tersedia di atas."
            f"{rag_part}{graph_part}"
        )

        stream_queue = stream_queue_var.get()
        # Retry up to 2x untuk plan generation
        plan = None
        manager_narrative = ""
        for attempt in range(3):
            try:
                logger.info(f"[Manager] Calling LLM for plan generation (attempt {attempt+1})")
                llm = get_llm_client()
                if stream_queue is not None:
                    # Streaming: dapatkan narasi + plan dalam satu call
                    stream = await llm.chat.completions.create(
                        model=OPENROUTER_MODEL,
                        messages=[
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        tools=[PLAN_TOOL],
                        tool_choice="auto",
                        stream=True,
                        timeout=60.0,
                    )
                    content = ""
                    args_buf = ""
                    async for chunk in stream:
                        delta = chunk.choices[0].delta if chunk.choices else None
                        if not delta:
                            continue
                        if delta.content:
                            content += delta.content
                            await stream_queue.put({
                                "_sse_event": "token",
                                "node_id": "manager",
                                "content": delta.content
                            })
                        if delta.tool_calls:
                            for tc in delta.tool_calls:
                                if tc.function and tc.function.arguments:
                                    args_buf += tc.function.arguments
                    manager_narrative = content
                    plan_raw = args_buf
                else:
                    res = await llm.chat.completions.create(
                        model=OPENROUTER_MODEL,
                        messages=[
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        tools=[PLAN_TOOL],
                        tool_choice="auto",
                        timeout=60.0,
                    )
                    msg = res.choices[0].message
                    manager_narrative = msg.content or ""
                    plan_raw = msg.tool_calls[0].function.arguments if msg.tool_calls else ""

                logger.critical(f"[Manager] === NARRATIVE ===")
                logger.critical(f"[Manager] {manager_narrative[:300]}")
                logger.critical(f"[Manager] === RAW PLAN ===")
                logger.critical(f"[Manager] {plan_raw}")
                logger.critical(f"[Manager] ================")

                if not plan_raw or not plan_raw.strip():
                    logger.info("[Manager] No plan generated — chat mode (greeting/general question)")
                    if manager_narrative:
                        await telemetry.emit(TelemetryEvent(
                            trace_id=trace_id, node_id="manager", node_type="Manager",
                            state=NodeState.DONE, narrative=manager_narrative
                        ))
                    return manager_narrative or "Halo! Ada yang bisa saya bantu terkait audit lingkungan Bali?"

                plan = MasterPlan(**json.loads(plan_raw))
                plan.trace_id = trace_id
                logger.critical(f"[Manager] === PARSED PLAN ===")
                for t in plan.tasks:
                    logger.critical(f"[Manager] Task: {t.task_id} | Agent: {t.target_agent} | Intent: {t.intent} | Deps: {t.depends_on}")
                logger.critical(f"[Manager] ====================")

                await telemetry.emit(TelemetryEvent(
                    trace_id=trace_id, node_id="manager", node_type="Manager",
                    state=NodeState.THINKING, narrative=manager_narrative or f"Menyusun rencana audit untuk: {prompt[:80]}...",
                    metadata={"phase": "planning"}
                ))
                self.context_chain["plan"] = plan
                self.context_chain["plan_narrative"] = manager_narrative or ""
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
            state=NodeState.THINKING, narrative=f"Menjalankan {len(plan.tasks)} agent: {', '.join(t.target_agent for t in plan.tasks)}...",
            metadata={"phase": "execute", "phase_step": "spawning", "task_count": len(plan.tasks)}
        ))

        logger.info(f"[Manager] Starting DAG execution with {len(plan.tasks)} tasks")
        all_manifests = registry.get_all_manifests()
        logger.debug(f"[Manager] Loaded {len(all_manifests)} tool manifests")

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
                deadlocked = [
                    (t.task_id, [d for d in t.depends_on if d not in completed_tasks])
                    for t in pending_tasks.values()
                ]
                logger.warning(f"[Manager] DAG Deadlock: {len(pending_tasks)} tasks stuck. "
                               f"Missing deps: { {tid: missing for tid, missing in deadlocked} }")
                await telemetry.emit(TelemetryEvent(
                    trace_id=trace_id, node_id="manager", node_type="Manager",
                    state=NodeState.ERROR,
                    narrative=f"DAG Deadlock: {len(pending_tasks)} tasks tidak bisa dijalankan (dependency hilang). Lanjut dengan partial."
                ))
                for tid, missing in deadlocked:
                    failed_tasks[tid] = {
                        "agent": pending_tasks[tid].target_agent,
                        "intent": pending_tasks[tid].intent,
                        "error": f"DAG Deadlock: depends on missing task(s): {missing}",
                        "error_type": "dag_deadlock"
                    }
                    shared_context[tid] = {"_ERROR_": {
                        "agent": pending_tasks[tid].target_agent,
                        "status": "DEADLOCK",
                        "detail": f"Depends on non-existent task(s): {missing}"
                    }}
                    completed_tasks.add(tid)
                pending_tasks.clear()
                break

            logger.debug(f"[Manager] Ready tasks: {[t.task_id for t in ready_tasks]}")
            for t in ready_tasks:
                if t.depends_on:
                    t.parameters["shared_data"] = {
                        d: shared_context.get(d, {"_DAG_INCOMPLETE_": f"Task '{d}' gagal atau tidak ada data."})
                        for d in t.depends_on
                    }
                    logger.debug(f"[Manager] Injected shared_data for task {t.task_id}: dependencies={t.depends_on}")

            coroutines = []
            for t in ready_tasks:
                scoped_manifests = get_scoped_manifests(t.target_agent, all_manifests)
                tools = [{"type": "function", "function": m} for m in scoped_manifests]
                logger.info(f"[Manager] Spawning SubAgent: {t.target_agent} for task {t.task_id}")
                sub = SubAgent(t, self.session_id, tools, trace_id)
                coroutines.append(execute_subagent_with_safety(sub, trace_id, timeout=45))

            logger.debug(f"[Manager] Gathering {len(coroutines)} SubAgent results")
            results = await asyncio.gather(*coroutines, return_exceptions=True)

            for t, res in zip(ready_tasks, results):
                if isinstance(res, Exception):
                    logger.error(f"[Manager] Task {t.task_id} crashed: {res}")
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
                    logger.warning(f"[Manager] Task {t.task_id} returned error: {res.get('error_code')}")
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
                    logger.critical(f"[Manager] Task {t.task_id} completed with LLM response")
                    logger.critical(f"[Manager] Response: {res['response'][:300]}")
                    shared_context[t.task_id] = {t.target_agent: res["response"]}
                else:
                    logger.critical(f"[Manager] Task {t.task_id} completed with tool results")
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
                logger.info(f"[Manager] Task {t.task_id} marked complete. Remaining: {len(pending_tasks)}")

                # Phase 2 Execute — progress THINKING event
                task_map = {tt.task_id: tt for tt in plan.tasks}
                done_agents = [task_map[tid].target_agent for tid in completed_tasks if tid in task_map]
                pending_agents = [task_map[tid].target_agent for tid in pending_tasks if tid in task_map]
                progress_narrative = f"{t.target_agent} selesai."
                if pending_agents:
                    progress_narrative += f" Menunggu: {', '.join(pending_agents)}..."
                else:
                    progress_narrative += " Semua agen selesai. Masuk ke validasi."
                self.context_chain["execute_narrative"].append(progress_narrative)
                await telemetry.emit(TelemetryEvent(
                    trace_id=trace_id, node_id="manager", node_type="Manager",
                    state=NodeState.THINKING, narrative=progress_narrative,
                    metadata={"phase": "execute", "phase_step": "progress",
                              "done": done_agents, "pending": pending_agents}
                ))

        # Phase 3: Validate hasil agent
        shared_context, failed_tasks, re_spawn_log, validate_summary = await self._phase_validate(
            shared_context, failed_tasks, plan, trace_id
        )
        self.context_chain["re_spawn_log"] = re_spawn_log
        self.context_chain["validate_summary"] = validate_summary
        raw_results = list(shared_context.values())

        logger.info(f"[Manager] Synthesizing final report from {len(raw_results)} results")
        plan_summary = json.dumps([
            {"task_id": t.task_id, "agent": t.target_agent, "intent": t.intent}
            for t in plan.tasks
        ])
        synth_input = {
            "user_request": self.context_chain["user_request"],
            "plan_summary": plan_summary,
            "execution_results": {
                "successful": [r for r in raw_results if "_ERROR_" not in r],
                "failed": [{"task_id": tid, **info} for tid, info in failed_tasks.items()],
            },
            "validation_summary": validate_summary,
            "re_spawn_attempts": re_spawn_log,
        }
        logger.debug(f"[Manager] Synthesis input: {len(synth_input.get('execution_results', {}).get('successful', []))} success, {len(synth_input.get('execution_results', {}).get('failed', []))} failed, {len(re_spawn_log)} re-spawns")

        synth_system = (
            "Anda adalah Report Synthesizer untuk audit lingkungan Bali.\n"
            "NARASI: ceritakan dulu ringkasan temuan audit dalam bahasa Indonesia.\n"
            "Setelah narasi, gunakan tool generate_report untuk output laporan final."
        )
        synth_payload = [
            {"role": "system", "content": synth_system},
            {"role": "user", "content": f"Synthesize these audit results into a comprehensive report. Include a section about any failed tasks if present:\n{json.dumps(synth_input)}"}
        ]
        synth_tools = [{
            "type": "function",
            "function": {
                "name": "generate_report",
                "description": "Generate the final audit report",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "report": {"type": "string", "description": "Full audit report text"}
                    },
                    "required": ["report"]
                }
            }
        }]

        report = ""
        synth_narrative = ""
        try:
            llm = get_llm_client()
            stream_queue = stream_queue_var.get()
            if stream_queue is not None:
                logger.debug("[Manager] Streaming synthesis LLM call")
                stream = await llm.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=synth_payload,
                    tools=synth_tools,
                    tool_choice="auto",
                    stream=True,
                    timeout=90.0,
                )
                content = ""
                args_buf = ""
                async for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if not delta:
                        continue
                    if delta.content:
                        content += delta.content
                        await stream_queue.put({
                            "_sse_event": "token",
                            "node_id": "manager",
                            "content": delta.content
                        })
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            if tc.function and tc.function.arguments:
                                args_buf += tc.function.arguments
                synth_narrative = content
                if args_buf:
                    report = json.loads(args_buf).get("report", "")
                if not report:
                    report = content or ""
            else:
                logger.debug("[Manager] Non-streaming synthesis LLM call")
                res_synth = await llm.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=synth_payload,
                    tools=synth_tools,
                    tool_choice="auto",
                    timeout=90.0,
                )
                msg = res_synth.choices[0].message
                synth_narrative = msg.content or ""
                if msg.tool_calls:
                    report = json.loads(msg.tool_calls[0].function.arguments).get("report", "")
                else:
                    report = msg.content or ""

            logger.critical(f"[Manager] === SYNTHESIS NARRATIVE ===")
            logger.critical(f"[Manager] {synth_narrative[:300]}")
            logger.critical(f"[Manager] === FINAL REPORT ===")
            logger.critical(f"[Manager] {report[:300]}")
            logger.critical(f"[Manager] =========================")

        except Exception as e:
            logger.error(f"[Manager] Synthesis LLM call failed: {e}")
            await telemetry.emit(TelemetryEvent(
                trace_id=trace_id, node_id="manager", node_type="Manager",
                state=NodeState.ERROR, narrative=f"Synthesis error: {str(e)[:100]}"
            ))
            return f"Error: Gagal menyusun laporan sintesis."

        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="manager", node_type="Manager",
            state=NodeState.THINKING, narrative=synth_narrative or "Menyusun laporan final berdasarkan data yang terkumpul...",
            metadata={"phase": "synthesis"}
        ))

        # Cognitive Memory: Extract temporal patterns and save to knowledge graph
        try:
            logger.debug("[Manager] Starting Cognitive Memory extraction")
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
                logger.debug(f"[Manager] Extracted snapshot with {len(snapshot.get('nodes', []))} nodes")

                # Build nodes and edges
                nodes = builder.build_nodes(snapshot)
                edges = builder.build_edges(snapshot, label_to_id)
                logger.debug(f"[Manager] Built {len(nodes)} nodes and {len(edges)} edges")

                # Insert into knowledge graph
                graph_result = insert_memory_graph(trace_id, nodes, edges)
                logger.info(f"[Manager] Knowledge Graph: {graph_result.get('nodes_created', 0)} nodes, {graph_result.get('edges_created', 0)} edges created")

                await telemetry.emit(TelemetryEvent(
                    trace_id=trace_id, node_id="manager", node_type="Manager",
                    state=NodeState.THINKING, narrative=f"Cognitive Memory: {graph_result.get('nodes_created', 0)} nodes linked."
                ))
        except Exception as e:
            logger.warning(f"[Manager] Cognitive Memory extraction failed (non-critical): {e}")
            await telemetry.emit(TelemetryEvent(
                trace_id=trace_id, node_id="manager", node_type="Manager",
                state=NodeState.ERROR, narrative=f"Cognitive Memory extraction (non-critical): {str(e)[:100]}"
            ))

        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="manager", node_type="Manager",
            state=NodeState.DONE, narrative=report,
            metadata={"phase": "done", "type": "final_report", "session_id": self.session_id}
        ))
        logger.info(f"[Manager] Emitting final DONE event with report")

        await asyncio.to_thread(store_semantic_memory, self.session_id, f"Audit Result: {report}")
        logger.info(f"[Manager] Semantic memory stored. Run complete.")
        return report