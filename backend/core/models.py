from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
import time

class NodeState(str, Enum):
    """
    Enum untuk merepresentasikan state dari suatu node dalam arsitektur DAG.
    Digunakan untuk stream telemetry SSE.
    """
    IDLE = "IDLE"
    THINKING = "THINKING"
    SPAWNING = "SPAWNING"
    EXECUTING = "EXECUTING"
    ERROR = "ERROR"
    DONE = "DONE"

class TaskIntent(BaseModel):
    """
    Spesifikasi instruksi tugas tunggal untuk dikirim ke Sub-Agent.
    """
    task_id: str = Field(description="ID unik task")
    depends_on: List[str] = Field(default=[], description="Daftar task_id yang harus selesai lebih dulu")
    target_agent: str = Field(description="Identifier sub-agent tujuan, misal: 'geo_agent', 'osint_agent'")
    intent: str = Field(description="Instruksi spesifik yang harus dieksekusi oleh sub-agent")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameter spesifik untuk modul yang dituju")
    execute_at: Optional[str] = Field(None, description="Timestamp jadwal eksekusi (format ISO) untuk mode autonomous")

class MasterPlan(BaseModel):
    """
    Output utama dari Manager Agent. Berisi daftar tugas terstruktur.
    """
    trace_id: str = Field(default="", description="Unique identifier untuk tracing eksekusi ini")
    tasks: List[TaskIntent] = Field(default_factory=list, description="Daftar task (intent) yang akan di-dispatch ke Sub-Agents")

class TelemetryEvent(BaseModel):
    """
    Payload log event yang akan dikirim secara real-time via Server-Sent Events (SSE) ke frontend.
    """
    trace_id: str = Field(description="ID sesi eksekusi yang sedang berjalan")
    node_id: str = Field(description="Identifier node yang sedang aktif, misal: 'manager_01', 'geo_worker'")
    node_type: str = Field(description="Tipe node: 'Manager', 'SubAgent', atau 'Module'")
    state: NodeState = Field(description="State saat ini dari node tersebut")
    narrative: str = Field(description="Chain-of-Thought (CoT) atau log deskriptif untuk di-render di UI")
    timestamp: int = Field(default_factory=lambda: int(time.time()), description="Unix timestamp event terjadi")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadata opsional: tool_name, duration_ms, rag_sources")

class ErrorResponse(BaseModel):
    """
    Standar response untuk error yang terstruktur.
    Digunakan saat Sub-Agent gagal setelah max retries,
    agar Manager tetap mendapat informasi dan bisa generate partial report.
    """
    status: str = Field(..., description="Status error: 'TOOL_EXECUTION_FAILED', 'TIMEOUT', 'VALIDATION_ERROR', 'UNKNOWN'")
    step: str = Field(..., description="Langkah di mana error terjadi: 'http_request', 'tool_execution', 'parsing', dll.")
    error_code: str = Field(..., description="Kode error spesifik: 'OPENROUTER_HTTP_500', 'SUB_AGENT_TIMEOUT', dll.")
    context: Dict[str, Any] = Field(default_factory=dict, description="Konteks tambahan: attempts, recommendation, dll.")
    
    # Method helper agar bisa dipakai sebagai dict
    def model_dump(self, **kwargs):
        return super().model_dump(**kwargs)

class SDUIConfig(BaseModel):
    """
    Konfigurasi visual dasar untuk Server-Driven UI (SDUI).
    """
    ui_type: str = Field(description="Tipe komponen frontend yang harus di-render, misal: 'map_layer', 'matrix_log', 'metric_card'")
    layout: str = Field(default="full_width", description="Layout komponen, misal: 'full_width', 'half_width'")
    theme: str = Field(default="minimalist", description="Tema komponen visual")

class SDUIPayload(BaseModel):
    """
    Format output final dari backend yang siap di-consume oleh frontend (Next.js) menggunakan arsitektur SDUI.
    """
    trace_id: str = Field(description="ID sesi eksekusi")
    module_name: str = Field(description="Nama modul yang menghasilkan data ini")
    display_config: SDUIConfig = Field(description="Konfigurasi UI untuk data ini")
    content: Dict[str, Any] = Field(description="Data aktual (payload) hasil proses modul")

# ═══════════════════════════════════════════════════════════════════
# SPRINT 5 — Autonomous Swarm + Laporan Store
# ═══════════════════════════════════════════════════════════════════

class CaseIntent(BaseModel):
    """Satu kasus audit yang diputuskan Agent Otak."""
    case_id: str = Field(..., description="Unique ID kasus, e.g. case-001")
    title: str = Field(..., min_length=5, description="Judul singkat kasus")
    intent: str = Field(..., min_length=10, description="Prompt lengkap untuk Agent Run")
    priority: int = Field(default=5, ge=1, le=10, description="Urgency 1-10")
    urgency_reason: str = Field(..., description="Kenapa prioritas segitu")

class AskQuestion(BaseModel):
    """Pertanyaan user untuk AiBubble scoped RAG."""
    question: str = Field(..., min_length=3, max_length=500)

class TaskCreate(BaseModel):
    """Bikin autonomous task dari UI."""
    intent_description: str = Field(..., min_length=5)
    execute_at: Optional[str] = Field(None, description="ISO8601 timestamp, default now")
    task_type: str = Field(default="autonomous", pattern="^(autonomous|direct)$")
    priority: int = Field(default=5, ge=1, le=10)
    recurrence_minutes: Optional[int] = Field(None, ge=1, description="Recurring interval in minutes")

class LaporanFilter(BaseModel):
    """Filter untuk GET /api/laporan."""
    source: Optional[str] = Field(None, pattern="^(autonomous|user)$")
    location: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)