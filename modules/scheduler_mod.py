import datetime
from typing import Dict, Any
from core.base_module import PemaliModule, ModuleOutput
from core.database import SessionLocal, AutonomousTask

class SystemSchedulerModule(PemaliModule):
    @property
    def manifest(self) -> Dict[str, Any]:
        return {
            "name": "system_scheduler",
            "description": "Menjadwalkan tugas otonom di masa depan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes_from_now": {"type": "integer", "description": "Berapa menit lagi tugas harus jalan."},
                    "intent": {"type": "string", "description": "Apa yang harus dilakukan agen nanti?"}
                },
                "required": ["minutes_from_now", "intent"]
            }
        }

    async def execute(self, params: Dict[str, Any], session_id: str = None) -> ModuleOutput:
        db = SessionLocal()
        try:
            # Proteksi tipe data agar tidak 400 Bad Request
            minutes = int(params.get("minutes_from_now", 1))
            intent = str(params.get("intent", "Check again"))
            
            execution_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes)
            
            new_task = AutonomousTask(
                execute_at=execution_time,
                intent_description=intent,
                status="pending"
            )
            db.add(new_task)
            db.commit()
            

            return ModuleOutput(
                status="success",
                data={"task_id": new_task.id, "scheduled_at": str(execution_time)},
                agent_hint=f"Tugas berhasil dijadwalkan untuk {minutes} menit lagi.",
                thk_alignment="Palemahan"  # Tambahkan ini agar validator tidak error
            )
        except Exception as e:
            print(f"[Scheduler] Error: {e}")
            return ModuleOutput(status="error", data={"error": str(e)}, agent_hint="Gagal menjadwalkan.")
        finally:
            db.close()