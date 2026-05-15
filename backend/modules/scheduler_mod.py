import datetime
from typing import Dict, Any, List

from pydantic import BaseModel, Field

from backend.core.base_module import (
    PemaliModuleV2, ModuleOutput, THKAlignment, THKPresets
)
from backend.core.database import SessionLocal, AutonomousTask


# =========================
# INPUT SCHEMA
# =========================
class SchedulerInput(BaseModel):
    """Schema input untuk penjadwalan task otonom."""

    delay_minutes: int = Field(
        ...,
        ge=1,
        description="Durasi tunda dari sekarang dalam menit sebelum task dijalankan."
    )
    intent: str = Field(
        ...,
        min_length=5,
        description="Instruksi atau objective tugas otonom yang akan dijalankan nanti."
    )


# =========================
# MODULE IMPLEMENTATION
# =========================
class SystemSchedulerModule(PemaliModuleV2):

    @property
    def name(self) -> str:
        return "system_scheduler"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return (
            "Menjadwalkan tugas otonom untuk dieksekusi di masa depan "
            "berdasarkan delay waktu tertentu. Task disimpan di database "
            "dan di-pickup oleh Worker Daemon."
        )

    @property
    def tags(self) -> List[str]:
        return ["scheduler", "autonomous"]

    @property
    def input_schema(self):
        return SchedulerInput

    @property
    def output_example(self) -> Dict[str, Any]:
        return {
            "status": 200,
            "data": {
                "task_id": 42,
                "task_status": "scheduled",
                "scheduled_execution_utc": "2026-05-16T10:30:00+00:00"
            },
            "agent_hint": "Task berhasil dijadwalkan. Worker daemon akan pickup dalam 60 menit.",
            "thk_alignment": {
                "parahyangan": "Penjadwalan dilakukan dengan integritas — task tercatat di database",
                "pawongan": "Task otonom traceable oleh sistem untuk transparansi penuh",
                "palemahan": "Otomatisasi audit rutin memungkinkan deteksi dini kerusakan lingkungan"
            }
        }

    async def execute(
        self,
        params: SchedulerInput,
        context: Dict[str, Any]
    ) -> ModuleOutput:

        db = SessionLocal()
        start_ms = self._now_ms()

        try:
            session_id = context.get("session_id", "unknown")
            current_utc = datetime.datetime.now(datetime.timezone.utc)
            execute_time = current_utc + datetime.timedelta(minutes=params.delay_minutes)

            new_task = AutonomousTask(
                execute_at=execute_time,
                intent_description=params.intent,
                context_snapshot={"parent_session": session_id},
                status="pending",
            )

            db.add(new_task)
            db.commit()
            db.refresh(new_task)

            execution_ms = round(self._now_ms() - start_ms, 2)
            data = {
                "task_id": new_task.id,
                "task_status": "scheduled",
                "intent": params.intent,
                "scheduled_execution_utc": execute_time.isoformat(),
                "delay_minutes": params.delay_minutes,
                "metadata": {
                    "created_at_utc": current_utc.isoformat(),
                    "parent_session": session_id,
                    "execution_ms": execution_ms,
                },
            }

            return ModuleOutput(
                status=200,
                data=data,
                agent_hint=(
                    f"Task #{new_task.id} dijadwalkan pada {execute_time.isoformat()} "
                    f"(delay {params.delay_minutes} menit). Intent: '{params.intent[:80]}'. "
                    f"Worker daemon akan pickup saat waktunya tiba."
                ),
                thk_alignment=THKPresets.autonomous_task(params.intent),
            )

        except Exception as e:
            db.rollback()
            execution_ms = round(self._now_ms() - start_ms, 2)
            return ModuleOutput(
                status=500,
                data={"execution_ms": execution_ms},
                error_msg=f"SystemSchedulerModule failed: {str(e)}",
                agent_hint="Gagal menjadwalkan task. Periksa koneksi database dan coba lagi.",
            )

        finally:
            db.close()