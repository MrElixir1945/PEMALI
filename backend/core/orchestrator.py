import json
import asyncio
import os
import re
import datetime
import time
import uuid
import logging
import contextvars
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI, APIError, APIConnectionError, APIStatusError
from backend.core.memory import query_semantic, query_memory_graph_for_context, store_semantic_memory, insert_memory_graph, query_semantic_scoped
from backend.core.database import SessionLocal, AuditLog, RawSensorData
from backend.core.memory_processor import TemporalPatternExtractor, KnowledgeGraphBuilder
from backend.core.models import MasterPlan, TaskIntent, TelemetryEvent, NodeState, ErrorResponse
from backend.core.telemetry import telemetry
from backend.core.registry import registry
from backend.core.llm_client import get_llm_client, rate_limit_wait
from backend.core.session_logger import SessionLogger

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
    "geo_agent": ["geo_*", "satellite_*", "mapping_*", "air_quality_*", "earthquake_*", "weather_*", "climate_*"],
    "water_agent": ["water_*", "hydrology_*", "sea_*", "marine_*"],
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


_IMAGE_RE = re.compile(
    r'(?:'
    r'https?://[^\s"\']+\.(?:png|jpg|jpeg|gif|webp|svg|bmp|ico)'  # absolute URL
    r'|'
    r'!\[.*?\]\(.*?\)'  # markdown image: ![alt](url)
    r'|'
    r'(?:\./)?[\w\-./]+\.(?:png|jpg|jpeg|gif|webp|svg|bmp|ico)'  # relative path
    r'|'
    r'data:image/[a-z+]+;base64,[^\s"\']+'  # data URI
    r'|'
    r'<img\s[^>]*src="[^"]*"[^>]*/?>'  # HTML img tag
    r'|'
    r'Cannot read ["\']?image\.png["\']?'  # specific LLM error message
    r'|'
    r'this model does not support image input'  # model error response
    r')',
    re.IGNORECASE
)

def _strip_image_urls(data: dict | list | str) -> dict | list | str:
    if isinstance(data, dict):
        return {k: _strip_image_urls(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_strip_image_urls(v) for v in data]
    if isinstance(data, str) and _IMAGE_RE.search(data):
        return _IMAGE_RE.sub('[image]', data)
    return data


def _sanitize_output(text: str) -> str:
    """Filter output dari LLM — strip error & image references sebelum dikirim ke user."""
    text = _strip_image_urls(text)
    # Nuclear filter: spesifik error pattern yg pernah muncul
    text = re.sub(
        r'ERROR:\s*Cannot read.*?does not support image input.*?Inform the user\..*',
        '[Sistem: Respon mengandung error LLM yang telah difilter]',
        text, flags=re.IGNORECASE | re.DOTALL
    )
    return text


def _sanitize_messages(messages: List[Dict]) -> List[Dict]:
    """Sanitize all messages before LLM call — strip image references."""
    serialized_before = json.dumps(messages, default=str, ensure_ascii=False)
    sanitized = _strip_image_urls(messages)
    serialized_after = json.dumps(sanitized, default=str, ensure_ascii=False)
    if serialized_before != serialized_after:
        logger.warning(f"[Sanitizer] Image references stripped: {serialized_before[:200]} -> {serialized_after[:200]}")
    return sanitized


class SubAgent:
    def __init__(self, task: TaskIntent, session_id: str, tools: List[Dict], trace_id: str):
        self.task = task
        self.session_id = session_id
        self.trace_id = trace_id
        self.tools = tools
        self.headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
        self.max_retries = 3

    async def _call_llm_streaming(self, messages: List[Dict]) -> Dict:
        """Stream LLM response via openai SDK. Push tokens to stream_queue + telemetry."""
        stream_queue = stream_queue_var.get()
        logger.debug(f"[SubAgent._call_llm_streaming] stream_queue={stream_queue is not None}, node_id={self.task.target_agent}")
        llm = get_llm_client()

        full_content = ""
        tool_call_accum: Dict[int, Dict] = {}

        # Token buffer: flush every 5 tokens or 200ms to reduce SSE overhead
        token_buffer: list[str] = []
        BUFFER_FLUSH_SIZE = 5
        last_flush = time.monotonic()
        BUFFER_FLUSH_INTERVAL = 0.2

        async def flush_token_buffer(phase: str = "reasoning"):
            nonlocal token_buffer, last_flush
            if not token_buffer:
                return
            batch = "".join(token_buffer)
            token_buffer = []
            last_flush = time.monotonic()
            await telemetry.emit_dict({
                "type": "agent_thinking",
                "agent_id": self.task.target_agent,
                "agent_name": self.task.target_agent.replace("_agent", "").replace("_", " ").title(),
                "chunk": batch,
                "phase": phase,
                "trace_id": self.trace_id,
                "timestamp": int(time.time())
            })

        messages = _sanitize_messages(messages)
        logger.info(f"[SubAgent] LLM call: model={OPENROUTER_MODEL} msgs={len(messages)} tools={len(self.tools) if self.tools else 0}")
        await rate_limit_wait()
        stream = await llm.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages,
            tools=self.tools if self.tools else None,
            tool_choice="auto" if self.tools else None,
            stream=True,
            max_tokens=4096,
            timeout=180.0,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            if delta.content:
                full_content += delta.content
                # Push to direct stream queue (for POST /api/stream consumers)
                if stream_queue is not None:
                    await stream_queue.put({
                        "_sse_event": "token",
                        "node_id": self.task.target_agent,
                        "content": delta.content
                    })
                # Buffer for telemetry broadcast (for /api/telemetry consumers)
                token_buffer.append(delta.content)
                if len(token_buffer) >= BUFFER_FLUSH_SIZE or \
                   (time.monotonic() - last_flush) >= BUFFER_FLUSH_INTERVAL:
                    await flush_token_buffer("reasoning")

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

        # Flush remaining tokens
        await flush_token_buffer("reasoning")

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
            "2. **WAJIB**: Tulis narrative dulu (2-4 kalimat) menjelaskan apa yang kamu pikirkan, "
            "mengapa tool ini relevan, dan apa yang kamu harapkan. JANGAN PERNAH SKIP LANGKAH INI.\n"
            "3. Setelah narrative, panggil tool yang relevan dari daftar # TOOLS.\n"
            "4. Setelah hasil tool masuk, interpretasikan data dalam narasi ringkas.\n\n"

            "# ATURAN NARASI (WAJIB DIBACA)\n"
            "Kamu HARUS menulis narrative thinking SEBELUM memanggil tool apapun.\n"
            "Narrative adalah cerita proses berpikirmu — bukan JSON, bukan data mentah.\n"
            "Format: tulis narrative natural dulu, BARU gunakan function calling untuk tool.\n"
            "JANGAN PERNAH memanggil tool tanpa narrative terlebih dahulu.\n"
            "Narasi dalam bahasa Indonesia natural, ringkas, informatif.\n\n"

            "# ATURAN RESPONSE\n"
            "KAMU WAJIB MENGIRIMKAN NARRATIVE + TOOL CALL DALAM SATU RESPONSE.\n"
            "Contoh yang BENAR:\n"
            "  <narrative>Saya akan memeriksa data suhu permukaan....</narrative>\n"
            "  <tool_call>weather_hazard_monitor(location=\"...\")</tool_call>\n\n"

            "Contoh yang SALAH (JANGAN DITIRU):\n"
            "  <tool_call>weather_hazard_monitor(location=\"...\")</tool_call>  "
            "(TANPA NARRATIVE — INI DILARANG!)\n\n"

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

        system_prompt = _strip_image_urls(system_prompt)
        messages = [{"role": "system", "content": system_prompt}]

        for attempt in range(self.max_retries):
            payload = {"model": OPENROUTER_MODEL, "messages": messages, "tools": self.tools, "tool_choice": "auto"}

            try:
                stream_queue = stream_queue_var.get()

                # Emit reasoning_start so frontend shows agent is active
                await telemetry.emit_dict({
                    "type": "agent_thinking",
                    "agent_id": self.task.target_agent,
                    "agent_name": self.task.target_agent.replace("_agent", "").replace("_", " ").title(),
                    "chunk": "",
                    "phase": "reasoning",
                    "trace_id": self.trace_id,
                    "timestamp": int(time.time())
                })

                if stream_queue is not None:
                    logger.info(f"[SubAgent] Streaming LLM (attempt {attempt+1}/{self.max_retries})")
                    ai_msg = await self._call_llm_streaming(messages)
                    logger.info(f"[SubAgent] Stream complete: {len(ai_msg.get('content',''))} chars")
                else:
                    logger.info(f"[SubAgent] Calling LLM non-streaming (attempt {attempt+1}/{self.max_retries})")
                    llm = get_llm_client()
                    messages = _sanitize_messages(messages)
                    await rate_limit_wait()
                    res = await llm.chat.completions.create(
                        model=OPENROUTER_MODEL,
                        messages=messages,
                        tools=self.tools if self.tools else None,
                        tool_choice="auto" if self.tools else None,
                        max_tokens=4096,
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
                    # For non-streaming, emit full content as single chunk
                    if ai_msg.get("content"):
                        await telemetry.emit_dict({
                            "type": "agent_thinking",
                            "agent_id": self.task.target_agent,
                            "agent_name": self.task.target_agent.replace("_agent", "").replace("_", " ").title(),
                            "chunk": ai_msg["content"],
                            "phase": "reasoning",
                            "trace_id": self.trace_id,
                            "timestamp": int(time.time())
                        })

                llm_narrative = ai_msg.get("content") or ""

                # Fallback: if LLM sent tool calls without narrative, generate auto-narrative
                if not llm_narrative and ai_msg.get("tool_calls"):
                    tool_names = [tc["function"]["name"] for tc in ai_msg["tool_calls"]]
                    llm_narrative = (
                        f"Menganalisis data menggunakan {', '.join(tool_names)} untuk "
                        f"mengevaluasi kondisi lingkungan di area target sesuai instruksi: "
                        f"{self.task.intent}"
                    )
                    # Emit fallback to global telemetry subscribers
                    await telemetry.emit_dict({
                        "type": "agent_thinking",
                        "agent_id": self.task.target_agent,
                        "agent_name": self.task.target_agent.replace("_agent", "").replace("_", " ").title(),
                        "chunk": llm_narrative,
                        "phase": "reasoning",
                        "trace_id": self.trace_id,
                        "timestamp": int(time.time())
                    })
                    # Also push to direct stream queue if available
                    stream_q = stream_queue_var.get()
                    if stream_q is not None:
                        await stream_q.put({
                            "_sse_event": "token",
                            "node_id": self.task.target_agent,
                            "content": llm_narrative
                        })

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

                messages.append(_strip_image_urls(ai_msg))

                if ai_msg.get("tool_calls"):
                    tool_names = [tc["function"]["name"] for tc in ai_msg["tool_calls"]]
                    logger.info(f"[SubAgent] Executing tools: {tool_names}")
                    await telemetry.emit(TelemetryEvent(
                        trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                        state=NodeState.EXECUTING, narrative=f"Menjalankan: {', '.join(tool_names)}"
                    ))
                    # Emit phase transition for frontend thinking stream
                    await telemetry.emit_dict({
                        "type": "agent_thinking",
                        "agent_id": self.task.target_agent,
                        "agent_name": self.task.target_agent.replace("_agent", "").replace("_", " ").title(),
                        "chunk": "",
                        "phase": "tool_call",
                        "tool_names": tool_names,
                        "trace_id": self.trace_id,
                        "timestamp": int(time.time())
                    })

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
                        sanitized = _strip_image_urls(res_data["output"])
                        messages.append({
                            "role": "tool",
                            "tool_call_id": res_data["tool_call_id"],
                            "name": res_data["tool_name"],
                            "content": json.dumps(sanitized)
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

            raw_payload = {}
            if output.data:
                raw_payload = output.data
                if isinstance(raw_payload, dict) and len(str(raw_payload)) > 50000:
                    raw_payload = {"_truncated": True, "size": len(str(output.data))}

            await telemetry.emit(TelemetryEvent(
                trace_id=self.trace_id, node_id=name, node_type="Module",
                state=NodeState.DONE, narrative=f"Modul [{name}] selesai.",
                metadata={
                    "tool_name": name, "duration_ms": duration_ms, "status": output.status,
                    "raw_payload": raw_payload,
                    "agent_hint": output.agent_hint,
                }
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
        self.mode = "human"
        self.source = "user"
        self.priority = 5
        self.case_title = None  # S5: title untuk autonomous reports
        self.strategic_context = ""
        self._started_at = time.time()

    def set_autonomous_mode(self, memory_context: str = "", source: str = "autonomous", priority: int = 5, case_title: str = None, strategic_context: str = ""):
        self.mode = "autonomous"
        self.memory_context = memory_context
        self.source = source
        self.priority = priority
        self.case_title = case_title or self.case_title
        self.strategic_context = strategic_context

    def _is_error_response(self, res: Dict) -> bool:
        return isinstance(res, dict) and res.get("status") in [
            "TOOL_EXECUTION_FAILED", "VALIDATION_ERROR", "TIMEOUT"
        ]

    async def _phase_validate(self, shared_context: Dict, failed_tasks: Dict, 
                              plan: "MasterPlan", trace_id: str) -> tuple:
        """Fase 3: Validasi hasil agent, trigger re-spawn jika ditemukan ketidaksesuaian data.
        
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
                sp_narrative = f"Perlu verifikasi ulang di {agent}: {reason_text}. Percobaan ke-{attempt}/{max_re_spawn}."
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
                f"Validasi: {success_count}/{len(shared_context)} agent berhasil."
                f" {len(anomalies)} memerlukan verifikasi ulang, "
                f"{len([r for r in re_spawn_log if r['status'] == 'success'])} tervalidasi."
            )
        else:
            validate_summary = f"Semua {success_count} agent valid dan data lengkap."

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
        rag_context = _strip_image_urls("\n".join([f"- {m['content']}" for m in past_memories])) if past_memories else ""
        graph_context = _strip_image_urls(graph_context) if graph_context else ""
        logger.debug(f"[Manager] RAG context: {len(past_memories)} memories, graph_context={bool(graph_context)}")

        rag_part = f"\n# KONTEKS HISTORIS (ChromaDB)\n{rag_context}\n" if rag_context else ""
        graph_part = f"\n# KONTEKS KNOWLEDGE GRAPH (PostgreSQL)\n{graph_context}\n" if graph_context else ""

        all_manifests = registry.get_all_manifests()
        tool_context = build_tool_context(all_manifests)

        if self.mode == "autonomous":
            mem_part = f"\n# MEMORY KONTEKS\n{self.memory_context}\n" if self.memory_context else ""
            strat_part = f"\n# KONTEKS STRATEGIS (Agent Otak)\n{self.strategic_context}\n" if self.strategic_context else ""
            sys_prompt = (
                "[PEMALI AUTONOMOUS AGENT RUN]\n"
                "Anda adalah AGENT RUN dalam sistem audit lingkungan Bali.\n"
                "Anda menjalankan SATU kasus audit yang sudah ditentukan oleh Agent Otak.\n"
                f"Priority: {self.priority}/10\n"
                f"{strat_part}\n"

                f"{tool_context}\n\n"

                "# TUGAS ANDA\n"
                "1. Analisis kasus yang diberikan — apa yang perlu diaudit?\n"
                "2. Buat rencana audit menggunakan tool create_audit_plan\n"
                "3. Jalankan Sub-Agent sesuai rencana\n"
                "4. Validasi hasil\n"
                "5. Buat laporan sintesis yang komprehensif\n\n"

                "# ATURAN NARASI\n"
                "Narasikan dulu dalam bahasa Indonesia sebelum membuat plan:\n"
                "- Apa yang kamu pahami dari kasus ini\n"
                "- Kenapa ini penting untuk lingkungan Bali\n"
                "- Agent mana yang cocok dan kenapa\n\n"

                "Agent yang tersedia: geo_agent, water_agent, fire_agent, osint_agent, scheduler_agent\n"
                f"{mem_part}"
                f"{rag_part}{graph_part}"
            )
            sys_prompt = _strip_image_urls(sys_prompt)
            plan_user_prompt = _strip_image_urls(f"Kasus yang harus diaudit:\n{prompt}")
        else:
            sys_prompt = (
                "[PEMALI NARRATIVE CONTRACT v1]\n"
                "Anda adalah MANAGER AGENT dalam sistem audit lingkungan Bali.\n\n"

                "# GATE LOGIC — PILIH SALAH SATU:\n"
                "---\n"
                "JALUR A — PERCAKAPAN BIASA:\n"
                "Gunakan jika user hanya: salam, sapaan, tanya kabar, obrolan ringan, atau pertanyaan umum.\n"
                "→ JAWAB LANGSUNG dengan narasi natural. JANGAN panggil tool apapun.\n"
                "→ JANGAN gunakan create_audit_plan. JANGAN spawn SubAgent.\n"
                "→ Cukup balas seperti asisten biasa.\n"
                "---\n"
                "JALUR B — PERMINTAAN AUDIT:\n"
                "Gunakan jika user meminta: data lingkungan, investigasi, audit kawasan, analisis Bali, "
                "informasi spesifik tentang cuaca/air/kebakaran/laut/polusi.\n"
                "→ Narasikan dulu analisis audit dalam bahasa Indonesia.\n"
                "→ Setelah narasi, panggil tool create_audit_plan dengan task terstruktur.\n"
                "---\n\n"

                f"{tool_context}\n\n"

                "Agent yang tersedia: geo_agent, water_agent, fire_agent, osint_agent, scheduler_agent\n"
                "depends_on untuk urutan DAG — task tanpa dependency dikerjakan paralel.\n"
                "PENTING: hanya assign task yang sesuai dengan tools yang tersedia di atas."
                f"{rag_part}{graph_part}"
            )
            sys_prompt = _strip_image_urls(sys_prompt)
            plan_user_prompt = _strip_image_urls(prompt)

        stream_queue = stream_queue_var.get()
        # Retry up to 2x untuk plan generation
        plan = None
        manager_narrative = ""
        last_error = ""
        for attempt in range(3):
            try:
                logger.info(f"[Manager] Calling LLM for plan generation (attempt {attempt+1}) model={OPENROUTER_MODEL}")
                llm = get_llm_client()
                await rate_limit_wait()

                msgs = _sanitize_messages([
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": plan_user_prompt}
                ])
                if last_error and attempt > 0:
                    msgs.append({
                        "role": "user",
                        "content": (
                            f"Perbaiki format JSON. Error sebelumnya:\n{last_error}\n\n"
                            "WAJIB gunakan format create_audit_plan dengan field 'tasks' "
                            "yang berisi array of objects, masing-masing dengan: "
                            "task_id, target_agent (pilih dari: geo_agent, water_agent, fire_agent, osint_agent), "
                            "intent, depends_on (array string)."
                        )
                    })

                if stream_queue is not None:
                    # Streaming: dapatkan narasi + plan dalam satu call
                    stream = await llm.chat.completions.create(
                        model=OPENROUTER_MODEL,
                        messages=_sanitize_messages([
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": plan_user_prompt}
                        ]),
                        tools=[PLAN_TOOL],
                        tool_choice="auto",
                        stream=True,
                        max_tokens=4096,
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
                        messages=_sanitize_messages([
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": plan_user_prompt}
                        ]),
                        tools=[PLAN_TOOL],
                        tool_choice="auto",
                        max_tokens=4096,
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
                            trace_id=trace_id, node_id="manager", node_type="Chat",
                            state=NodeState.DONE, narrative=manager_narrative,
                            metadata={"type": "chat_response"}
                        ))
                    return _sanitize_output(manager_narrative) or "Halo! Ada yang bisa saya bantu terkait audit lingkungan Bali?"

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

                # S5: Emit plan event for /agentic live feed
                plan_event_metadata: Dict[str, Any] = {
                    "phase": "execute", "phase_step": "plan",
                    "plan": [
                        {
                            "task_id": t.task_id,
                            "agent": t.target_agent,
                            "intent": t.intent[:150],
                            "depends_on": t.depends_on,
                        }
                        for t in plan.tasks
                    ]
                }
                # Attach case info if autonomous mode
                if self.mode == "autonomous":
                    plan_event_metadata["case_id"] = getattr(self, 'case_title', None)
                    plan_event_metadata["case_title"] = getattr(self, 'case_title', None)
                await telemetry.emit(TelemetryEvent(
                    trace_id=trace_id, node_id="manager", node_type="Manager",
                    state=NodeState.THINKING,
                    narrative=f"Rencana audit: {len(plan.tasks)} task — {', '.join(t.target_agent for t in plan.tasks)}",
                    metadata=plan_event_metadata,
                ))
                break
            except Exception as e:
                last_error = str(e)[:300]
                logger.error(f"[Manager] Plan generation FAILED attempt {attempt+1}: {last_error}", exc_info=True)
                if attempt < 2:
                    await telemetry.emit(TelemetryEvent(
                        trace_id=trace_id, node_id="manager", node_type="Manager",
                        state=NodeState.ERROR, narrative=f"Plan retry {attempt+1}: {str(e)[:200]}"
                    ))
                    await asyncio.sleep(1)
                else:
                    await telemetry.emit(TelemetryEvent(
                        trace_id=trace_id, node_id="manager", node_type="Manager",
                        state=NodeState.ERROR, narrative=f"Plan Error: {str(e)[:300]}"
                    ))
                    return f"Error: {str(e)[:500]}"

        if not plan:
            return "Error: Gagal menyusun rencana."

        planned_agents = list(set(t.target_agent for t in plan.tasks))

        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="manager", node_type="Manager",
            state=NodeState.THINKING, narrative=f"Menjalankan {len(plan.tasks)} agent: {', '.join(t.target_agent for t in plan.tasks)}...",
            metadata={"phase": "execute", "phase_step": "spawning", "task_count": len(plan.tasks), "planned_agents": planned_agents}
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

            # Sequential execution to avoid free tier rate limits
            results = []
            for t in ready_tasks:
                scoped_manifests = get_scoped_manifests(t.target_agent, all_manifests)
                tools = [{"type": "function", "function": m} for m in scoped_manifests]
                logger.info(f"[Manager] Spawning SubAgent: {t.target_agent} for task {t.task_id}")
                sub = SubAgent(t, self.session_id, tools, trace_id)
                # Delay antar subagent buat hindarin rate limit
                if results:
                    await asyncio.sleep(4)
                try:
                    res = await execute_subagent_with_safety(sub, trace_id, timeout=45)
                except Exception as exc:
                    res = exc
                results.append(res)

            logger.debug(f"[Manager] Gathered {len(results)} SubAgent results")

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
                        clean_output = _strip_image_urls(r.copy())
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

        # Delay buat hindarin rate limit dari subagent calls sebelumnya
        await asyncio.sleep(3)

        # Siapkan hasil module dengan konteks — task ID di-anonymize, tapi tool_name + agent_hint tetap
        anon_successful = []
        for i, r in enumerate(raw_results):
            if "_ERROR_" in r:
                continue
            entries = []
            for key, val in r.items():
                entry = {"tool": key}
                if isinstance(val, dict):
                    entry["agent_hint"] = val.get("agent_hint", "")
                    if "data" in val:
                        entry["data"] = val["data"]
                    elif "output" in val:
                        entry["data"] = val["output"]
                    else:
                        entry["data"] = val
                else:
                    entry["data"] = val
                entries.append(entry)
            anon_successful.append({"task_index": i + 1, "results": entries})

        anon_failed = []
        for i, (tid, info) in enumerate(failed_tasks.items()):
            anon_failed.append({"task_index": i+1, "agent": info.get("agent", "unknown"), "error": info.get("error", "unknown"), "error_type": info.get("error_type", "")})

        synth_input = {
            "user_request": self.context_chain["user_request"],
            "execution_results": {
                "successful": anon_successful,
                "failed": anon_failed,
            },
            "validation_summary": validate_summary,
            "re_spawn_attempts": re_spawn_log,
        }
        logger.debug(f"[Manager] Synthesis input: {len(synth_input.get('execution_results', {}).get('successful', []))} success, {len(synth_input.get('execution_results', {}).get('failed', []))} failed, {len(re_spawn_log)} re-spawns")

        synth_system = (
            "Anda adalah Report Synthesizer untuk audit lingkungan Bali.\n"
            "TUGAS: Generate laporan audit berdasarkan DATA NYATA dari sensor/modul di bawah.\n\n"
            "# FORMAT LAPORAN (WAJIB)\n"
            "1. Gunakan markdown heading: # untuk judul utama, ## untuk section, ### untuk subsection\n"
            "2. JANGAN gunakan === atau --- sebagai separator section — gunakan heading markdown\n"
            "3. JANGAN gunakan ALL CAPS untuk heading — gunakan Title Case atau Kalimat Biasa\n"
            "4. Struktur: # Judul Laporan → ## Ringkasan Eksekutif → ## Temuan → ## Rekomendasi → ## Kesimpulan\n"
            "5. Gunakan bullet points dan numbered list untuk data sensor\n"
            "6. Paragraf pendek (max 4 kalimat per paragraf)\n\n"
            "# ATURAN BAHASA (WAJIB)\n"
            "1. BAHASA INDONESIA baku — jangan campur bahasa asing, Polandia, atau Jerman.\n"
            "2. Ejaan baku: 'sinar' bukan 'sin', 'kemungkinan' bukan 'możliwość', 'berteduh' bukan 'berbayang'.\n"
            "3. Gunakan istilah sains standar: 'suhu' (bukan temperature), 'kelembaban' (bukan humidity).\n"
            "4. JANGAN gunakan kata-kata dari bahasa lain selain Indonesia dan Inggris teknis terbatas.\n\n"
            "# ATURAN DATA\n"
            "1. BACA semua data di execution_results dengan saksama — setiap field.\n"
            "2. GUNAKAN data beneran dari sensor — jangan mengarang atau menggeneralisasi.\n"
            "3. Jika data sensor menyebutkan angka/lokasi/spesifik, sebutkan dalam laporan.\n"
            "4. JANGAN invent data — jika data kosong/null, tulis 'Tidak tersedia' bukan mengarang.\n"
            "5. Jangan sebutkan nama agen internal (geo_agent, osint_agent, dll), nama tool, atau struktur task.\n"
            "6. Jangan sebutkan 'Task Index' atau 'Rencana Audit' atau 'Execution Results'.\n"
            "7. FOKUS pada: temuan, data sensor, pola dan tren, analisis, rekomendasi, kesimpulan.\n"
            "8. Gunakan tool generate_report untuk output laporan final."
        )
        synth_payload = [
            {"role": "system", "content": synth_system},
            {"role": "user", "content": _strip_image_urls(
                f"Synthesize these audit results into a comprehensive report. Include a section about any failed tasks if present:\n{json.dumps(synth_input)}"
            )}
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

            # Helper: flush token buffer for synthesis phase
            _synth_buffer: list[str] = []
            async def _flush_synth():
                nonlocal _synth_buffer
                if not _synth_buffer:
                    return
                batch = "".join(_synth_buffer)
                _synth_buffer = []
                await telemetry.emit_dict({
                    "type": "agent_thinking",
                    "agent_id": "manager",
                    "agent_name": "Manager",
                    "chunk": batch,
                    "phase": "synthesis",
                    "trace_id": trace_id,
                    "timestamp": int(time.time())
                })

            if stream_queue is not None:
                logger.debug("[Manager] Streaming synthesis LLM call")
                synth_payload = _sanitize_messages(synth_payload)
                await rate_limit_wait()
                stream = await llm.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=synth_payload,
                    tools=synth_tools,
                    tool_choice="auto",
                    stream=True,
                    max_tokens=8192,
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
                        _synth_buffer.append(delta.content)
                        if len(_synth_buffer) >= 5:
                            await _flush_synth()
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            if tc.function and tc.function.arguments:
                                args_buf += tc.function.arguments
                await _flush_synth()
                synth_narrative = content
                if args_buf:
                    report = json.loads(args_buf).get("report", "")
                if not report:
                    report = content or ""
            else:
                logger.debug("[Manager] Non-streaming synthesis LLM call")
                synth_payload = _sanitize_messages(synth_payload)
                await rate_limit_wait()
                res_synth = await llm.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=synth_payload,
                    tools=synth_tools,
                    tool_choice="auto",
                    max_tokens=8192,
                    timeout=90.0,
                )
                msg = res_synth.choices[0].message
                synth_narrative = msg.content or ""
                if msg.tool_calls:
                    report = json.loads(msg.tool_calls[0].function.arguments).get("report", "")
                else:
                    report = msg.content or ""
                # Emit full narrative as single chunk for frontend typewriter
                if synth_narrative:
                    await telemetry.emit_dict({
                        "type": "agent_thinking",
                        "agent_id": "manager",
                        "agent_name": "Manager",
                        "chunk": synth_narrative,
                        "phase": "synthesis",
                        "trace_id": trace_id,
                        "timestamp": int(time.time())
                    })

            logger.critical(f"[Manager] === SYNTHESIS NARRATIVE ===")
            logger.critical(f"[Manager] {synth_narrative[:300]}")
            logger.critical(f"[Manager] === FINAL REPORT ===")
            logger.critical(f"[Manager] {report[:300]}")
            logger.critical(f"[Manager] =========================")

            # Retry jika report kosong atau kena rate limit
            retry_delays = [2, 6, 15]  # exponential backoff
            for retry_idx, delay in enumerate(retry_delays):
                if report and len(report.strip()) >= 100:
                    break
                reason = "empty report" if not report else f"short report ({len(report)} chars)"
                logger.warning(f"[Manager] Synthesis {reason} — retry {retry_idx+1}/{len(retry_delays)} after {delay}s")
                await asyncio.sleep(delay)
                try:
                    synth_payload = _sanitize_messages(synth_payload)
                    await rate_limit_wait()
                    res_retry = await llm.chat.completions.create(
                        model=OPENROUTER_MODEL,
                        messages=synth_payload,
                        tools=synth_tools,
                        tool_choice={"type": "function", "function": {"name": "generate_report"}},
                        max_tokens=4096,
                        timeout=120.0,
                    )
                    msg = res_retry.choices[0].message
                    synth_narrative = msg.content or synth_narrative
                    if msg.tool_calls:
                        report = json.loads(msg.tool_calls[0].function.arguments).get("report", "")
                    if not report:
                        report = msg.content or ""
                    logger.info(f"[Manager] Synthesis retry got {len(report)} chars")
                except Exception as e2:
                    logger.error(f"[Manager] Synthesis retry failed: {e2}")

            # Validasi: cek apakah report benar-benar merujuk data module
            if report and len(report) > 200:
                data_keywords = []
                for task in anon_successful:
                    for entry in task.get("results", []):
                        hint = entry.get("agent_hint", "")
                        if hint:
                            words = [w for w in hint.lower().split() if len(w) > 4]
                            data_keywords.extend(words[:10])
                if data_keywords:
                    matched = sum(1 for kw in data_keywords if kw in report.lower())
                    ratio = matched / len(data_keywords)
                    if ratio < 0.1 and len(data_keywords) > 3:
                        logger.warning(f"[Manager] Report validation: hanya {matched}/{len(data_keywords)} keyword dari module data yang muncul di report (ratio={ratio:.2f}) — kemungkinan model tidak merujuk data sensor")
                    else:
                        logger.info(f"[Manager] Report validation: {matched}/{len(data_keywords)} keyword muncul (ratio={ratio:.2f})")

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
                label_to_id = {}
                for i, node in enumerate(nodes):
                    label = node.get("label")
                    if label:
                        label_to_id[label] = i + 1
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

        # Emit synthesis DONE event for frontend auto-redirect
        if report:
            await telemetry.emit(TelemetryEvent(
                trace_id=trace_id, node_id="synthesis", node_type="Manager",
                state=NodeState.DONE, narrative=report,
                metadata={"phase": "synthesis", "type": "final_report", "session_id": self.session_id}
            ))

        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="manager", node_type="Manager",
            state=NodeState.DONE, narrative=report,
            metadata={"phase": "done", "type": "final_report", "session_id": self.session_id}
        ))
        logger.info(f"[Manager] Emitting final DONE event with report")

        # ── SPRINT 5: Save to DB + ChromaDB paralel ──
        try:
            await asyncio.gather(
                asyncio.to_thread(self._save_audit_log, report, shared_context, failed_tasks),
                asyncio.to_thread(self._save_raw_sensor_data, shared_context),
                asyncio.to_thread(store_semantic_memory, self.session_id, f"Audit Result: {report}"),
            )
            logger.info(f"[Manager] DB saves dispatched (PostgreSQL + ChromaDB)")
        except Exception as e:
            logger.error(f"[Manager] DB save error (non-critical): {e}")

        logger.info(f"[Manager] Semantic memory stored. Run complete.")

        # ── Save full JSON session dump ──
        try:
            self._save_full_json(report, shared_context, failed_tasks, trace_id)
        except Exception as e:
            logger.error(f"[Save] Full JSON error (non-critical): {e}")

        return _sanitize_output(report) if report else report

    # ═════════════════════════════════════════════════════════════
    # SPRINT 5 — Database persistence helpers
    # ═════════════════════════════════════════════════════════════

    def _save_audit_log(self, report: str, shared_context: Dict, failed_tasks: Dict):
        """Save final report to audit_logs table."""
        if not report or len(report.strip()) < 50:
            logger.warning(f"[Save] Skipping empty report for session {self.session_id}")
            return

        db = SessionLocal()
        try:
            # Extract location and issue_type from context
            if self.mode == "autonomous" and self.case_title:
                location = self.case_title[:120]
            else:
                location = self.context_chain.get("user_request", "")[:120] if self.context_chain else ""
            issue_type = ""
            if shared_context:
                # Try to extract from first successful result
                for v in shared_context.values():
                    if isinstance(v, dict) and "_ERROR_" not in v:
                        issue_type = list(v.keys())[0] if v else ""
                        break

            # Build THK alignment from module outputs
            thk = {
                "parahyangan": "Data audit dikumpulkan dengan integritas dan divalidasi melalui pipeline 4-fase.",
                "pawongan": f"Laporan tersedia untuk transparansi. {len(shared_context)} agent berkontribusi.",
                "palemahan": "Audit ini mendukung kelestarian lingkungan Bali melalui deteksi dini perubahan kondisi lingkungan."
            }

            sub_agents = list(set(
                t.get("target_agent", "") or t.get("agent", "")
                for t in (self.context_chain.get("plan", MasterPlan(tasks=[])).model_dump().get("tasks", [])
                         if self.context_chain and self.context_chain.get("plan") else [])
            ))

            tool_count = sum(
                len(v) if isinstance(v, dict) else 1
                for v in shared_context.values()
                if isinstance(v, dict) and "_ERROR_" not in v
            )

            duration_ms = round((time.time() - self._started_at) * 1000)

            # S5: Fix title — autonomous pakai case_title, bukan system prompt
            if self.mode == "autonomous":
                if self.case_title:
                    report_title = self.case_title[:120]
                else:
                    # Fallback: first meaningful line of report
                    first_line = (report or "").split('\n')[0].strip('# -').strip()
                    report_title = first_line[:120] if first_line else "Laporan Audit Otonom"
            else:
                report_title = (self.context_chain.get("user_request", "") or "")[:120] if self.context_chain else ""

            # S5: Clean metadata prompt — jangan kirim full system prompt
            if self.mode == "autonomous":
                prompt_saved = (self.case_title or "")[:200]
            else:
                prompt_saved = (self.context_chain.get("user_request", "") or "")[:200] if self.context_chain else ""

            log = AuditLog(
                session_id=self.session_id,
                source=self.source,
                title=report_title or "Laporan Audit",
                priority=self.priority,
                location=location,
                issue_type=issue_type or "environmental_audit",
                narrative_report=report,
                thk_alignment=thk,
                metadata_json={
                    "prompt": prompt_saved,
                    "sub_agents": sub_agents,
                    "phases": ["planning", "execute", "validate", "synthesis", "done"],
                    "tool_calls": tool_count,
                    "tool_success": tool_count - len(failed_tasks),
                    "tool_errors": len(failed_tasks),
                    "failed_tasks": {tid: info.get("error", "unknown") for tid, info in failed_tasks.items()},
                    "duration_ms": duration_ms,
                },
            )
            db.add(log)
            db.commit()
            log_id = log.id
            logger.info(f"[Save] AuditLog #{log.id} saved (source={self.source}, priority={self.priority})")

            # Save report as .txt file jika ada konten
            if report and len(report.strip()) > 50:
                try:
                    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
                    os.makedirs(reports_dir, exist_ok=True)

                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_title = re.sub(r'[^\w\s-]', '', report_title or "laporan")[:80].strip().replace(' ', '_')
                    filename = f"{ts}_{safe_title}_{log_id}.txt"
                    filepath = os.path.join(reports_dir, filename)

                    header = f"{'='*60}\nPEMALI Audit Report #{log_id}\n{'='*60}\n"
                    header += f"Title: {report_title}\n"
                    header += f"Priority: {self.priority}/10\n"
                    header += f"Source: {self.source}\n"
                    header += f"Created: {ts}\n"
                    header += f"{'='*60}\n\n"

                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(header + report)

                    logger.info(f"[Save] Report saved to {filepath}")
                except Exception as e:
                    logger.warning(f"[Save] Failed to write report file: {e}")
        except Exception as e:
            db.rollback()
            logger.error(f"[Save] AuditLog failed: {e}")
        finally:
            db.close()

    def _save_raw_sensor_data(self, shared_context: Dict):
        """Save each successful sub-agent result to raw_sensor_data table."""
        db = SessionLocal()
        try:
            count = 0
            for task_id, data in shared_context.items():
                if not data or "_ERROR_" in data:
                    continue
                if isinstance(data, dict):
                    for tool_key, tool_data in data.items():
                        if tool_key.startswith("_"):
                            continue
                        record = RawSensorData(
                            session_id=self.session_id,
                            agent_name=task_id,
                            task_id=task_id,
                            tool_name=tool_key,
                            raw_payload=tool_data if isinstance(tool_data, dict) else {"value": str(tool_data)},
                        )
                        db.add(record)
                        count += 1
                else:
                    record = RawSensorData(
                        session_id=self.session_id,
                        agent_name=task_id,
                        task_id=task_id,
                        tool_name="llm_response",
                        raw_payload={"response": str(data)[:5000]},
                    )
                    db.add(record)
                    count += 1

            if count > 0:
                db.commit()
                logger.info(f"[Save] RawSensorData: {count} records saved")
        except Exception as e:
            db.rollback()
            logger.error(f"[Save] RawSensorData failed: {e}")
        finally:
            db.close()

    def _save_full_json(self, report: str, shared_context: Dict, failed_tasks: Dict, trace_id: str):
        """Save full session JSON to backend/reports/ — all data for one case."""
        if not report or len(report.strip()) < 50:
            return

        ctx = self.context_chain or {}
        plan = ctx.get("plan")

        # Extract agent results from shared_context
        agents_results = {}
        for task_id, data in shared_context.items():
            if data and "_ERROR_" in data:
                agents_results[task_id] = {"status": "failed", "error": str(data["_ERROR_"])}
            elif isinstance(data, dict):
                tools = {}
                for k, v in data.items():
                    if not k.startswith("_"):
                        tools[k] = v
                agents_results[task_id] = {"status": "success", "tools": tools}
            else:
                agents_results[task_id] = {"status": "success", "response": str(data)[:2000]}

        # Plan tasks
        plan_tasks = []
        if plan and hasattr(plan, "tasks"):
            plan_tasks = [
                {"task_id": t.task_id, "agent": t.target_agent, "intent": t.intent, "depends_on": t.depends_on}
                for t in plan.tasks
            ]

        # Summary
        total_agents = len(plan_tasks)
        total_failed = len(failed_tasks)

        session = {
            "meta": {
                "trace_id": trace_id,
                "session_id": self.session_id,
                "prompt": ctx.get("user_request", ""),
                "mode": self.mode,
                "source": self.source,
                "priority": self.priority,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
            "plan": {
                "narrative": ctx.get("plan_narrative", ""),
                "tasks": plan_tasks,
            },
            "execution": {
                "narratives": ctx.get("execute_narrative", []),
                "validate_summary": ctx.get("validate_summary", ""),
                "re_spawn_log": ctx.get("re_spawn_log", []),
            },
            "agents": agents_results,
            "failed_tasks": {tid: str(info.get("error", "unknown"))[:500] for tid, info in failed_tasks.items()},
            "final_report": report,
            "summary": {
                "agents_total": total_agents,
                "agents_success": total_agents - total_failed,
                "agents_failed": total_failed,
            },
        }

        reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
        os.makedirs(reports_dir, exist_ok=True)

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_id = re.sub(r'[^\w-]', '', self.session_id)[:30]
        filename = f"{ts}_{safe_id}_full.json"
        filepath = os.path.join(reports_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"[Save] Full JSON saved to {filepath} ({len(json.dumps(session))} bytes)")