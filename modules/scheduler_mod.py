import datetime
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from core.base_module import PemaliModuleV2, ModuleOutput
from core.database import SessionLocal, AutonomousTask

class SchedulerInput(BaseModel):
    minutes_from_now: int = Field(..., description="Waktu tunda dalam hitungan menit sebelum AI Agent dibangunkan kembali.")
    intent: str = Field(..., description="Deskripsi lengkap mengenai apa yang harus dikerjakan agen saat bangun nanti.")
    priority: str = Field(default="normal", description="Prioritas tugas: 'low', 'normal', atau 'high'.")

class SystemSchedulerModule(PemaliModuleV2):
    name = "system_scheduler"
    description = "Mengatur jadwal agar AI Agent dapat melakukan inspeksi atau tugas otonom di masa depan tanpa pemicu dari user."
    input_schema = SchedulerInput
    depends_on: List[str] = []

    async def execute(self, params: SchedulerInput, context: Dict[str, Any]) -> ModuleOutput:
        db = SessionLocal()
        try:
            # 1. Parameter sudah tervalidasi otomatis
            session_id = context.get("session_id", "default_session")
            execution_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=params.minutes_from_now)
            
            # 2. TULIS LOGIKA KERJA DI SINI
            # Menyimpan snapshot dari context yang ada agar AI nanti ingat konteks tugas
            context_snapshot = {
                "original_session_id": session_id,
                "priority": params.priority,
                "scheduled_by": "system_scheduler"
            }
            
            new_task = AutonomousTask(
                execute_at=execution_time,
                intent_description=params.intent,
                context_snapshot=context_snapshot,
                status="pending"
            )
            db.add(new_task)
            db.commit()
            
            # 3. Kembalikan output sesuai standar ModuleOutput V2
            return ModuleOutput(
                status=200,
                data={
                    "task_id": new_task.id, 
                    "scheduled_at": str(execution_time),
                    "intent": params.intent,
                    "session": session_id,
                    "message": f"Tugas berhasil dijadwalkan untuk {params.minutes_from_now} menit lagi dengan prioritas {params.priority}."
                },
                error_msg=None
            )
            
        except Exception as e:
            # 4. Tangani error agar Self-Correction AI dapat mengevaluasi ulang
            print(f"[Scheduler] Error: {e}")
            db.rollback()
            return ModuleOutput(
                status=500,
                data={},
                error_msg=f"Gagal menjadwalkan tugas otonom: {str(e)}"
            )
        finally:
            db.close()