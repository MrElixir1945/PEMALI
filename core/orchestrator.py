import json
import requests
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple
from sqlalchemy.orm import Session
from core.database import SessionLocal, AgentMemory
from core.memory import query_semantic, store_semantic_memory  # [NEW] Import Memory Layer

# Configuration
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
API_BASE = "http://localhost:8000"
OPENROUTER_KEY = "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"

class PemaliOrchestrator:
    def __init__(self, session_id: str, model: str = "deepseek/deepseek-v4-flash"):
        self.session_id = session_id
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "X-Title": "PEMALI V2.1 Orchestrator"
        }
        self.completed_tools: Set[str] = set()

    def _get_db(self):
        return SessionLocal()

    def _fetch_tools(self) -> List[Dict]:
        try:
            res = requests.get(f"{API_BASE}/tools", timeout=5)
            return [{"type": "function", "function": m} for m in res.json()]
        except Exception as e:
            print(f"[Orchestrator] Discovery error: {e}")
            return []

    def _save(self, db: Session, role: str, content: str, name: str = None, t_id: str = None):
        db.add(AgentMemory(
            session_id=self.session_id, 
            role=role, 
            content=content, 
            name=name,
            tool_call_id=t_id
        ))
        db.commit()

    def _run_scl_check(self, t_name: str, t_args: Dict, manifest: Optional[Dict]) -> Optional[str]:
        if not manifest:
            return f"Hallucinated tool: '{t_name}' is not registered."
        
        deps = manifest.get("depends_on", [])
        missing_deps = [d for d in deps if d not in self.completed_tools]
        if missing_deps:
            return f"DAG Violation: Prerequisites {missing_deps} must be executed successfully first."
            
        required_args = manifest.get("parameters", {}).get("required", [])
        missing_args = [req for req in required_args if req not in t_args]
        if missing_args:
            return f"Schema Violation: Missing required parameters {missing_args}."
            
        return None

    async def _execute_tool_async(self, t_name: str, t_args: Dict) -> Dict:
        def _call():
            return requests.post(f"{API_BASE}/execute", json={
                "session_id": self.session_id,
                "tool_name": t_name,
                "parameters": t_args
            }, timeout=30).json()
        
        try:
            return await asyncio.to_thread(_call)
        except Exception as e:
            return {"status": 500, "error_msg": str(e)}

    # [UPDATED] Tambah param rag_context
    async def _scout_phase(self, db: Session, tools: List[Dict], prompt: str, feedback: Optional[str] = None, rag_context: str = "") -> str:
        messages = [{
            "role": "system", 
            "content": (
                "You are SCOUT. Gather data using tools. "
                "STRICT DAG RULE: Check 'depends_on' before executing. "
                "For CROSS-VALIDATION, you can call multiple tools simultaneously. "
                "Output a detailed factual summary of your findings."
            )
        }]

        user_content = f"Task: {prompt}"
        
        # [NEW] Inject RAG Memory ke Prompt
        if rag_context:
            user_content += f"\n\n[HISTORICAL MEMORY (RAG)]:\n{rag_context}"
            
        if feedback:
            user_content += f"\n\n[SYSTEM SCL/FALLBACK] CRITIC feedback: {feedback}\nFix gaps or cross-validate and retry."
            
        messages.append({"role": "user", "content": user_content})
        self._save(db, "user", user_content, name="Scout_Input")

        for _ in range(4):
            payload = {"model": self.model, "messages": messages, "tools": tools, "tool_choice": "auto"}
            res = await asyncio.to_thread(requests.post, OPENROUTER_URL, headers=self.headers, json=payload)
            res_json = res.json()
            
            if "choices" not in res_json: break

            ai_msg = res_json['choices'][0]['message']
            messages.append(ai_msg)
            self._save(db, "assistant", ai_msg.get("content") or "", name="Scout")

            if not ai_msg.get("tool_calls"):
                break 

            tasks = []
            tool_contexts = []
            
            for tool_call in ai_msg["tool_calls"]:
                t_id = tool_call["id"]
                t_name = tool_call["function"]["name"]
                t_args = json.loads(tool_call["function"]["arguments"])
                manifest = next((t["function"] for t in tools if t["function"]["name"] == t_name), None)
                
                scl_error = self._run_scl_check(t_name, t_args, manifest)
                
                if scl_error:
                    obs = {"status": 400, "error_msg": f"[SCL INTERCEPT] {scl_error}"}
                    tasks.append(asyncio.sleep(0, result=obs))
                else:
                    tasks.append(self._execute_tool_async(t_name, t_args))
                
                tool_contexts.append((t_id, t_name))

            results = await asyncio.gather(*tasks)

            for (t_id, t_name), obs in zip(tool_contexts, results):
                if obs.get("status") == 200:
                    self.completed_tools.add(t_name)
                    
                messages.append({"role": "tool", "tool_call_id": t_id, "name": t_name, "content": json.dumps(obs)})
                self._save(db, "tool", json.dumps(obs), name=t_name, t_id=t_id)

        return messages[-1].get("content") or "No textual summary provided."

    async def _critic_phase(self, db: Session, scout_summary: str) -> Tuple[bool, str, float]:
        sys_prompt = (
            "You are CRITIC. Audit SCOUT REPORT for Tri Hita Karana alignment & data convergence. "
            "Calculate 'confidence_score' (0.0-1.0) based on evidence strength. "
            "Respond ONLY in JSON: {\"status\": \"APPROVED\"|\"REJECTED\", \"confidence_score\": float, \"reason\": \"critique details if rejected or low confidence\", \"final_response\": \"final output if approved\"}"
        )
        
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"SCOUT REPORT:\n{scout_summary}"}
        ]

        payload = {"model": self.model, "messages": messages, "response_format": {"type": "json_object"}}
        res = await asyncio.to_thread(requests.post, OPENROUTER_URL, headers=self.headers, json=payload)
        res_json = res.json()
        
        if "choices" not in res_json:
            return False, "Critic API Failed.", 0.0

        audit_res = res_json['choices'][0]['message']['content']
        self._save(db, "assistant", audit_res, name="Critic_Audit")

        try:
            audit_json = json.loads(audit_res)
            is_approved = audit_json.get("status") == "APPROVED"
            confidence = float(audit_json.get("confidence_score", 0.0))
            msg = audit_json.get("final_response") if is_approved else audit_json.get("reason")
            return is_approved, str(msg), confidence
        except Exception as e:
            return False, f"JSON Parse Error: {str(e)}", 0.0

    async def run(self, prompt: str):
        db = self._get_db()
        tools = self._fetch_tools()
        feedback = None
        max_iterations = 3

        # [NEW] Semantic Query Retrieval sebelum masuk loop
        past_memories = query_semantic(prompt, n_results=2)
        rag_context = "\n".join([f"- {m['content']}" for m in past_memories]) if past_memories else ""

        for attempt in range(max_iterations):
            # Pass RAG context ke Scout
            scout_summary = await self._scout_phase(db, tools, prompt, feedback, rag_context)
            is_approved, result, confidence = await self._critic_phase(db, scout_summary)

            if is_approved:
                if confidence >= 0.8:
                    # [NEW] Simpan kesimpulan akhir ke Memory Layer jika confidence tinggi
                    store_semantic_memory(
                        session_id=self.session_id,
                        text_content=f"Task: {prompt}\nConclusion: {result}",
                        metadata={"confidence": confidence, "type": "final_report"}
                    )
                    db.close()
                    return result
                else:
                    feedback = f"Status APPROVED but CONFIDENCE LOW ({confidence}). Must cross-validate using secondary tools before commit."
            else:
                feedback = result 

        db.close()
        return f"[SYSTEM ALERT] Audit aborted after {max_iterations} loops. Last status: {feedback}"