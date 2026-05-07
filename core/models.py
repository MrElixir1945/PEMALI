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
    trace_id: str = Field(description="Unique identifier untuk tracing eksekusi ini")
    tasks: List[TaskIntent] = Field(description="Daftar task (intent) yang akan di-dispatch ke Sub-Agents")

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