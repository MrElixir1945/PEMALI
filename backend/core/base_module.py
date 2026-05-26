import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Optional, Literal
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════
# KONTRAK OUTPUT — ModuleOutput V2 (backward-compatible)
# ═══════════════════════════════════════════════════════════════════

class THKAlignment(BaseModel):
    """
    Tri Hita Karana alignment — wajib diisi tiap modul.
    
    parahyangan  : hubungan spiritual (integritas data, kebenaran)
    pawongan     : hubungan sosial (transparansi, kolaborasi)
    palemahan    : hubungan alam (dampak lingkungan, keberlanjutan)
    """
    parahyangan: str = Field(
        ...,
        min_length=1,
        description="Spiritual balance — bagaimana modul ini menjaga integritas dan kebenaran data"
    )
    pawongan: str = Field(
        ...,
        min_length=1,
        description="Social collaboration — dampak dan transparansi ke pemangku kepentingan"
    )
    palemahan: str = Field(
        ...,
        min_length=1,
        description="Environmental aspect — dampak modul terhadap kelestarian alam Bali"
    )


class ModuleOutput(BaseModel):
    """
    Kontrak output standar PEMALI.
    
    Field wajib   : status, data, agent_hint, thk_alignment
    Field opsional: error_msg (untuk self-correction AI)
    """
    status: int = Field(
        ...,
        description="HTTP-style: 200=OK, 400=BadParams, 500=InternalError"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Hasil teknis mentah (raw payload dari sensor/API)"
    )
    agent_hint: str = Field(
        default="",
        description="Narasi singkat untuk AI agent — apa arti data ini, apa langkah selanjutnya"
    )
    thk_alignment: Optional[THKAlignment] = Field(
        default=None,
        description="Tri Hita Karana alignment. Wajib diisi untuk modul produksi."
    )
    error_msg: Optional[str] = Field(
        default=None,
        description="Detail error untuk self-correction AI. Hanya diisi saat status != 200."
    )

    @property
    def status_label(self) -> Literal["success", "error"]:
        """String label untuk kompatibilitas UTI V2 spec."""
        return "success" if self.status == 200 else "error"

    @property
    def is_ok(self) -> bool:
        return self.status == 200


# ═══════════════════════════════════════════════════════════════════
# PRESET THK — pilihan umum biar kontributor gak bingung
# ═══════════════════════════════════════════════════════════════════

class THKPresets:
    """Preset THKAlignment untuk use-case umum di audit lingkungan Bali."""

    @staticmethod
    def environmental_sensor(sensor_name: str, location: str) -> THKAlignment:
        return THKAlignment(
            parahyangan=f"Data '{sensor_name}' dikumpulkan tanpa manipulasi — apa adanya dari sensor",
            pawongan=f"Hasil pantauan '{sensor_name}' di '{location}' dapat diakses publik untuk transparansi",
            palemahan=f"Pemantauan '{sensor_name}' membantu deteksi dini kerusakan lingkungan di '{location}'"
        )

    @staticmethod
    def data_processing(source: str) -> THKAlignment:
        return THKAlignment(
            parahyangan=f"Data dari '{source}' diproses dengan algoritma yang transparan dan terverifikasi",
            pawongan=f"Hasil olahan '{source}' dibagikan ke pemangku kepentingan tanpa bias",
            palemahan=f"Analisis '{source}' mendukung pengambilan keputusan berbasis data untuk kelestarian Bali"
        )

    @staticmethod
    def autonomous_task(intent: str) -> THKAlignment:
        return THKAlignment(
            parahyangan="Penjadwalan otonom dilakukan dengan penuh tanggung jawab dan integritas",
            pawongan=f"Task '{intent[:60]}' dijadwalkan transparan — traceable oleh sistem",
            palemahan="Otomatisasi mengurangi beban operasional sehingga respons insiden lebih cepat"
        )


# ═══════════════════════════════════════════════════════════════════
# INTERFACE PEMALI MODULE V2
# ═══════════════════════════════════════════════════════════════════

class PemaliModuleV2(ABC):
    """
    Base class untuk SEMUA modul PEMALI.
    
    Contract:
    - name, description, input_schema: WAJIB override via @property
    - execute(): WAJIB implement, return ModuleOutput
    - version, tags, output_example: opsional, direkomendasikan
    - setup(), teardown(), validate_self(): lifecycle hooks opsional
    
    Discovery: auto-loaded oleh ModuleRegistry dari backend/modules/
    """
    name: str
    description: str
    input_schema: Type[BaseModel]
    depends_on: List[str] = []
    version: str = "0.1.0"
    tags: List[str] = []
    output_example: Optional[Dict[str, Any]] = None

    async def setup(self, context: Dict[str, Any]) -> None:
        """
        Dipanggil SEKALI sebelum execute().
        Gunakan untuk: buka koneksi DB, init HTTP session, preload cache.
        """
        pass

    @abstractmethod
    async def execute(self, params: BaseModel, context: Dict[str, Any]) -> ModuleOutput:
        """
        Logika inti modul.
        
        params  : Pydantic model — sudah divalidasi registry via input_schema
        context : dict dengan 'session_id' — bisa ditambahin field oleh orchestrator
        
        Wajib return ModuleOutput dengan agent_hint dan thk_alignment.
        """
        pass

    async def teardown(self, context: Dict[str, Any]) -> None:
        """
        Dipanggil SEKALI setelah execute().
        Gunakan untuk: tutup koneksi DB, release HTTP session, cleanup resource.
        """
        pass

    def validate_self(self) -> List[str]:
        """
        Self-check modul sebelum register.
        Return list error (string), kosong = valid.
        Override untuk validasi custom (misal: cek env vars, cek koneksi).
        """
        errors: List[str] = []
        if not self.name or not self.name.strip():
            errors.append("name tidak boleh kosong")
        if not self.description or not self.description.strip():
            errors.append("description tidak boleh kosong")
        if self.input_schema is None:
            errors.append("input_schema wajib didefinisikan")
        return errors

    @staticmethod
    def _now_ms() -> float:
        """Timestamp untuk pengukuran execution_ms."""
        return time.monotonic() * 1000