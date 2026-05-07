import json
import httpx
import asyncio
import os
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from core.database import SessionLocal, AgentMemory
from core.memory import query_semantic, store_semantic_memory
from core.models import MasterPlan, TaskIntent, TelemetryEvent, NodeState
from core.telemetry import telemetry
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")

class SubAgent:
    """Worker terisolasi yang menjalankan instruksi spesifik dengan kemampuan Self-Healing."""
    def __init__(self, task: TaskIntent, session_id: str, tools: List[Dict], trace_id: str):
        self.task = task
        self.session_id = session_id
        self.trace_id = trace_id
        self.tools = tools 
        self.headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
        self.max_retries = 3 # Batas maksimal untuk self-correction

    async def execute(self) -> Dict:
        await telemetry.emit(TelemetryEvent(
            trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
            state=NodeState.THINKING, narrative=f"Menganalisis instruksi: {self.task.intent}..."
        ))

        # System prompt ditambahkan instruksi self-correction
        messages = [{"role": "system", "content": f"You are {self.task.target_agent}. Task: {self.task.intent}. If tool execution fails, read the error message and fix your parameters."}]
        
        for attempt in range(self.max_retries):
            payload = {"model": OPENROUTER_MODEL, "messages": messages, "tools": self.tools, "tool_choice": "auto"}
            
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    res = await client.post(OPENROUTER_URL, headers=self.headers, json=payload)
                    res.raise_for_status()
                    ai_msg = res.json()['choices'][0]['message']
                    
                    # Append history agar AI ingat apa yang dia lakukan sebelumnya
                    messages.append(ai_msg)
                    
                    if ai_msg.get("tool_calls"):
                        await telemetry.emit(TelemetryEvent(
                            trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                            state=NodeState.EXECUTING, narrative=f"Eksekusi tools (Attempt {attempt+1}/{self.max_retries})..."
                        ))

                        tasks = []
                        for tc in ai_msg["tool_calls"]:
                            t_name = tc["function"]["name"]
                            t_args = json.loads(tc["function"]["arguments"])
                            tasks.append(self._execute_tool(t_name, t_args, tc["id"]))
                        
                        results = await asyncio.gather(*tasks)
                        
                        has_error = False
                        final_results = []
                        
                        for res_data in results:
                            # Masukkan output modul ke memory percakapan LLM
                            messages.append({
                                "role": "tool",
                                "tool_call_id": res_data["tool_call_id"],
                                "name": res_data["tool_name"],
                                "content": json.dumps(res_data["output"])
                            })
                            final_results.append(res_data["output"])
                            
                            # Deteksi apakah modul gagal (Validation 400 atau Execution 500)
                            if res_data["output"].get("status") in [400, 500]:
                                has_error = True
                        
                        if has_error and attempt < self.max_retries - 1:
                            await telemetry.emit(TelemetryEvent(
                                trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                                state=NodeState.THINKING, narrative="Mendeteksi error modul. Melakukan self-correction..."
                            ))
                            continue # Paksa AI mikir ulang dengan membaca error di 'messages'
                        
                        await telemetry.emit(TelemetryEvent(
                            trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                            state=NodeState.DONE, narrative="Sub-task selesai."
                        ))
                        return {"agent": self.task.target_agent, "results": final_results}
                    
                    # Jika tidak ada tool call, kembalikan respons teks biasa
                    return {"agent": self.task.target_agent, "response": ai_msg.get("content")}
                    
            except Exception as e:
                # Tangani Network Error (seperti 429 Too Many Requests)
                if attempt < self.max_retries - 1:
                    await telemetry.emit(TelemetryEvent(
                        trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                        state=NodeState.ERROR, narrative=f"Network Error. Retrying in 3s (Attempt {attempt+1})..."
                    ))
                    await asyncio.sleep(3)
                    continue
                else:
                    await telemetry.emit(TelemetryEvent(
                        trace_id=self.trace_id, node_id=self.task.target_agent, node_type="SubAgent",
                        state=NodeState.ERROR, narrative=f"Fatal Error: {str(e)}"
                    ))
                    return {"error": str(e)}
                    
        return {"error": "Max retries reached."}

    async def _execute_tool(self, name: str, args: Dict, tool_call_id: str) -> Dict:
        """Modifikasi sedikit untuk membawa tool_call_id agar LLM bisa mapping hasilnya."""
        await telemetry.emit(TelemetryEvent(
            trace_id=self.trace_id, node_id=name, node_type="Module",
            state=NodeState.EXECUTING, narrative=f"Eksekusi modul {name}..."
        ))
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(f"{API_BASE}/api/execute", json={
                    "session_id": self.session_id, "tool_name": name, "parameters": args
                })
                return {"tool_call_id": tool_call_id, "tool_name": name, "output": res.json()}
        except Exception as e:
            return {"tool_call_id": tool_call_id, "tool_name": name, "output": {"status": 500, "error_msg": str(e)}}

class PemaliOrchestrator:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}

    async def run(self, prompt: str):
        trace_id = f"tr-{int(datetime.datetime.now().timestamp())}"
        
        # 1. Manager Planning
        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="manager", node_type="Manager",
            state=NodeState.THINKING, narrative="Menyusun Master Plan berbasis RAG..."
        ))

        past_memories = query_semantic(prompt, n_results=2)
        rag_context = "\n".join([f"- {m['content']}" for m in past_memories]) if past_memories else ""

        sys_prompt = (
            "You are MANAGER AGENT. Analyze and delegate. "
            "Output JSON matching: {'trace_id': 'string', 'tasks': [{'task_id': 'string', 'target_agent': 'string', 'intent': 'string', 'depends_on': ['task_id']}]}"
        )
        
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": f"{sys_prompt}\nContext: {rag_context}"},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(OPENROUTER_URL, headers=self.headers, json=payload)
            res.raise_for_status()
            plan_raw = res.json()['choices'][0]['message']['content']
        
        try:
            plan = MasterPlan(**json.loads(plan_raw))
            plan.trace_id = trace_id
        except Exception as e:
            await telemetry.emit(TelemetryEvent(trace_id=trace_id, node_id="manager", node_type="Manager", state=NodeState.ERROR, narrative=f"Plan Error: {e}"))
            return f"Error: {e}"

        # 2. DAG Execution
        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="manager", node_type="Manager",
            state=NodeState.SPAWNING, narrative=f"Menjalankan {len(plan.tasks)} tugas dalam urutan DAG..."
        ))

        tools = await self._fetch_tools()
        shared_context = {}
        completed_tasks = set()
        pending_tasks = {t.task_id: t for t in plan.tasks}

        while pending_tasks:
            # Ambil task yang dependensinya sudah selesai semua
            ready_tasks = [
                t for t in pending_tasks.values() 
                if all(dep in completed_tasks for dep in t.depends_on)
            ]

            if not ready_tasks:
                raise ValueError("DAG Deadlock terdeteksi: Circular dependency.")

            # Injeksi shared_context ke prompt Sub-Agent
            for t in ready_tasks:
                if t.depends_on:
                    t.intent += f"\n[SHARED DATA]: {json.dumps({d: shared_context[d] for d in t.depends_on})}"

            # Eksekusi task yang siap secara paralel
            coroutines = [SubAgent(t, self.session_id, tools, trace_id).execute() for t in ready_tasks]
            results = await asyncio.gather(*coroutines)

            # Update state
            for t, res in zip(ready_tasks, results):
                shared_context[t.task_id] = res
                completed_tasks.add(t.task_id)
                del pending_tasks[t.task_id]

        raw_results = list(shared_context.values())

        # 3. Final Aggregation
        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="manager", node_type="Manager",
            state=NodeState.THINKING, narrative="Sintesis laporan final..."
        ))

        synth_payload = {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": f"Synthesize: {json.dumps(raw_results)}"}]
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            res_synth = await client.post(OPENROUTER_URL, headers=self.headers, json=synth_payload)
            report = res_synth.json()['choices'][0]['message']['content']

        await telemetry.emit(TelemetryEvent(trace_id=trace_id, node_id="manager", node_type="Manager", state=NodeState.DONE, narrative="Audit selesai."))
        
        store_semantic_memory(self.session_id, f"Audit Result: {report}")
        return report

    async def _fetch_tools(self) -> List[Dict]:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{API_BASE}/api/tools")
            return [{"type": "function", "function": m} for m in res.json()]