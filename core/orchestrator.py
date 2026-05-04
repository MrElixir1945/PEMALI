import json
import httpx
import datetime
import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from core.database import SessionLocal, AgentMemory, AutonomousTask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Config
OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")

if not OPENROUTER_KEY:
    print("[Warning] OPENROUTER_KEY not found in environment variables!")

class PemaliOrchestrator:
    def __init__(self, session_id: str, model: str = None):
        self.session_id = session_id
        self.model = model or OPENROUTER_MODEL
        print(f"[Orchestrator] Active Session: {self.session_id} | Model: {self.model}")
        self.headers = {
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json"
        }

    def _get_db(self):
        return SessionLocal()

    async def _fetch_tools(self) -> List[Dict]:
        """Discovery manifest dari FastAPI."""
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{API_BASE}/tools", timeout=5)
                return [{"type": "function", "function": m} for m in res.json()]
        except Exception as e:
            print(f"[Orchestrator] Failed to fetch tools: {e}")
            return []

    def _rehydrate(self, db: Session) -> List[Dict]:
        """Tarik history dari DB (Context Recovery)."""
        memories = db.query(AgentMemory).filter(
            AgentMemory.session_id == self.session_id
        ).order_by(AgentMemory.created_at.asc()).all()
        
        return [{"role": m.role, "content": m.content or "", "name": m.name} for m in memories]

    def _save(self, db: Session, role: str, content: str, name: str = None):
        """Persist step ke DB."""
        db.add(AgentMemory(session_id=self.session_id, role=role, content=content, name=name))
        db.commit()

    async def run(self, prompt: Optional[str] = None):
        db = self._get_db()
        tools = await self._fetch_tools()
        messages = self._rehydrate(db)

        if not messages:
            messages.append({
                "role": "system", 
                "content": (
                    "You are PEMALI AI, an autonomous agent. "
                    "STRICT RULE: Do not just describe your actions in text. "
                    "You MUST execute tools (satellite_mod, report_writer, system_scheduler) "
                    "to complete your tasks. If you need to schedule a follow-up, "
                    "you MUST call 'system_scheduler' tool. NO EXCEPTIONS."
                )
            })
        if prompt:
            self._save(db, "user", prompt)
            messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            for _ in range(5): # Max 5 loops
                payload = {"model": self.model, "messages": messages, "tools": tools, "tool_choice": "auto"}
                try:
                    print(f"[Orchestrator] Requesting LLM ({self.model})...")
                    res = await client.post(OPENROUTER_URL, headers=self.headers, json=payload, timeout=60)
                    print(f"[Orchestrator] HTTP {res.status_code}")
                    res_data = res.json()
                    
                    if 'error' in res_data:
                        print(f"[Orchestrator] OpenRouter Error: {res_data['error']}")
                        break
                        
                    if not res_data.get('choices'):
                        print(f"[Orchestrator] No choices in response: {res_data}")
                        break

                    ai_msg = res_data['choices'][0]['message']
                    print(f"[Orchestrator] AI Response: {ai_msg.get('content')[:50]}...")
                    self._save(db, "assistant", ai_msg.get("content") or "")
                    messages.append(ai_msg)

                    if not ai_msg.get("tool_calls"):
                        break

                    for tool in ai_msg["tool_calls"]:
                        t_name = tool["function"]["name"]
                        t_args = json.loads(tool["function"]["arguments"])
                        
                        # Execute via Communicate Layer
                        obs_res = await client.post(f"{API_BASE}/execute", json={
                            "session_id": self.session_id,
                            "tool_name": t_name,
                            "parameters": t_args
                        })
                        obs = obs_res.json()

                        messages.append({
                            "role": "tool", 
                            "tool_call_id": tool["id"], 
                            "name": t_name, 
                            "content": json.dumps(obs)
                        })
                except Exception as e:
                    print(f"[Orchestrator] Loop Error: {e}")
                    break

        db.close()
        return messages[-1]["content"] if messages else "No response generated."
