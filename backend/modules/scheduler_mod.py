import datetime
from typing import Dict, Any

from pydantic import BaseModel, Field

from backend.core.base_module import PemaliModuleV2, ModuleOutput
from backend.core.database import SessionLocal, AutonomousTask


# =========================
# INPUT SCHEMA
# =========================
class SchedulerInput(BaseModel):

    delay_minutes: int = Field(
        ...,
        description="Jumlah menit dari waktu sekarang sebelum tugas dijalankan."
    )

    intent: str = Field(
        ...,
        description="Instruksi atau objective tugas otonom yang akan dijalankan."
    )


# =========================
# MODULE IMPLEMENTATION
# =========================
class SystemSchedulerModule(PemaliModuleV2):

    @property
    def name(self) -> str:
        return "system_scheduler"

    @property
    def description(self) -> str:
        return (
            "Menjadwalkan tugas otonom untuk dieksekusi "
            "di masa depan berdasarkan delay waktu tertentu."
        )

    @property
    def input_schema(self):
        return SchedulerInput

    async def execute(
        self,
        params: SchedulerInput,
        context: Dict[str, Any]
    ) -> ModuleOutput:

        db = SessionLocal()

        try:
            session_id = context.get("session_id", "unknown")

            current_utc = datetime.datetime.now(
                datetime.timezone.utc
            )

            execute_time = current_utc + datetime.timedelta(
                minutes=params.delay_minutes
            )

            new_task = AutonomousTask(
                execute_at=execute_time,
                intent_description=params.intent,
                context_snapshot={
                    "parent_session": session_id
                },
                status="pending"
            )

            db.add(new_task)
            db.commit()
            db.refresh(new_task)

            return ModuleOutput(
                status=200,
                data={
                    "task_id": new_task.id,

                    "task_status": "scheduled",

                    "intent": params.intent,

                    "scheduled_execution_utc":
                        execute_time.isoformat(),

                    "metadata": {
                        "created_at_utc":
                            current_utc.isoformat(),

                        "parent_session":
                            session_id
                    }
                }
            )

        except Exception as e:
            db.rollback()

            return ModuleOutput(
                status=500,
                error_msg=f"SystemSchedulerModule failed: {str(e)}"
            )

        finally:
            db.close()