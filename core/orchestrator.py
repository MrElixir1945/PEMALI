import json
import requests
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from core.database import SessionLocal, AgentMemory, AutonomousTask

# Config
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
API_BASE = "http://localhost:8000"
OPENROUTER_KEY = "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"

class PemaliOrchestrator:
    def __init__(self, session_id: str, model: str = "deepseek/deepseek-chat"):
        self.session_id = session_id
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json"
        }

    def _get_db(self):
        return SessionLocal()

    def _fetch_tools(self) -> List[Dict]:
        """Discovery manifest dari FastAPI."""
        try:
            res = requests.get(f"{API_BASE}/tools", timeout=5)
            return [{"type": "function", "function": m} for m in res.json()]
        except Exception:
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
        tools = self._fetch_tools()
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

        for _ in range(5): # Max 5 loops
            payload = {"model": self.model, "messages": messages, "tools": tools, "tool_choice": "auto"}
            res = requests.post(OPENROUTER_URL, headers=self.headers, json=payload).json()
            
            ai_msg = res['choices'][0]['message']
            self._save(db, "assistant", ai_msg.get("content") or "")
            messages.append(ai_msg)

            if not ai_msg.get("tool_calls"):
                break

            for tool in ai_msg["tool_calls"]:
                t_name = tool["function"]["name"]
                t_args = json.loads(tool["function"]["arguments"])
                
                # Execute via Communicate Layer
                obs = requests.post(f"{API_BASE}/execute", json={
                    "session_id": self.session_id,
                    "tool_name": t_name,
                    "parameters": t_args
                }).json()

                messages.append({"role": "tool", "tool_call_id": tool["id"], "name": t_name, "content": json.dumps(obs)})

        db.close()
        return messages[-1]["content"]