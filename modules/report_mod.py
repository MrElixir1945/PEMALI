from typing import Dict, Any
from core.base_module import PemaliModule, ModuleOutput
from core.database import SessionLocal, AuditLog

class ReportWriterModule(PemaliModule):
    @property
    def manifest(self) -> Dict[str, Any]:
        return {
            "name": "report_writer",
            "description": "Menyimpan laporan audit final ke database setelah analisis selesai.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Lokasi spesifik audit."},
                    "issue_type": {"type": "string", "description": "Kategori masalah (misal: Alih Fungsi Lahan)."},
                    "narrative_report": {"type": "string", "description": "Narasi laporan lengkap dari AI."},
                    "thk_alignment": {"type": "string", "enum": ["Parahyangan", "Pawongan", "Palemahan"], "description": "Pilar Tri Hita Karana yang terdampak."}
                },
                "required": ["location", "issue_type", "narrative_report", "thk_alignment"]
            }
        }

    async def execute(self, params: Dict[str, Any]) -> ModuleOutput:
        db = SessionLocal()
        try:
            new_log = AuditLog(
                location=params["location"],
                issue_type=params["issue_type"],
                narrative_report=params["narrative_report"],
                thk_alignment=params["thk_alignment"],
                metadata_json={"source": "PEMALI_Autonomous_Agent"}
            )
            db.add(new_log)
            db.commit()
            
            return ModuleOutput(
                status="success",
                data={"log_id": new_log.id},
                agent_hint="Laporan telah berhasil disimpan di database permanen. Tugas selesai.",
                thk_alignment=params["thk_alignment"]
            )
        except Exception as e:
            return ModuleOutput(status="error", data={"error": str(e)}, agent_hint="Gagal menyimpan laporan.")
        finally:
            db.close()