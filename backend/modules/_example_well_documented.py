"""
╔══════════════════════════════════════════════════════════════════════╗
║  PEMALI MODULE — Example Well-Documented (Kanonik)                   ║
║                                                                      ║
║  Nama file: _example_well_documented.py                              ║
║  Prefiks _  : Tidak di-load otomatis oleh registry (template saja)   ║
║  Tujuan     : Referensi copy-paste untuk kontributor modul baru      ║
║                                                                      ║
║  Gunakan: cp _example_well_documented.py my_new_module.py            ║
╚══════════════════════════════════════════════════════════════════════╝

---MACHINE MANIFEST (dibaca registry & AI agent)---
module_name    : "water_quality_sensor"
version        : "1.0.0"
tags           : ["water", "environment"]
depends_on     : []
input_schema   : "WaterQualityInput"
requires_env   : ["WATER_API_KEY"]
requires_network : true
external_apis  : ["https://api.waterdata.bali.go.id"]
rate_limit_rps : 5
timeout_ms     : 30000
author         : "Rio <rio@pemali.dev>"
created        : "2026-05-15"
---

Modul ini adalah CONTOH KANONIK untuk pengembangan modul PEMALI.
Tunjukkan:
  - Kontrak output lengkap (status, data, agent_hint, thk_alignment)
  - Error handling terstruktur dengan agent_hint yang informatif
  - Lifecycle hooks (setup/teardown)
  - Metadata tagging untuk auto-scoping
  - Pengukuran execution_ms

CATATAN: Modul ini menggunakan API fiktif. Ganti dengan API/data source sesungguhnya.
"""

import asyncio
import random
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field, field_validator

from backend.core.base_module import (
    PemaliModuleV2,
    ModuleOutput,
    THKAlignment,
    THKPresets,
)


# ═══════════════════════════════════════════════════════════════════
# INPUT SCHEMA
# ═══════════════════════════════════════════════════════════════════

class WaterQualityInput(BaseModel):
    """
    Input untuk sensor kualitas air.

    Field description WAJIB diisi — LLM pakai ini untuk menentukan
    parameter saat function calling.
    """

    river_name: str = Field(
        ...,
        description="Nama sungai di Bali, e.g. 'Tukad Ayung', 'Tukad Petanu'",
        examples=["Tukad Ayung", "Tukad Badung"],
    )

    sample_date: Optional[str] = Field(
        default=None,
        description="Tanggal sampel ISO format YYYY-MM-DD. Default: hari ini.",
    )

    metrics: List[str] = Field(
        default_factory=lambda: ["ph", "turbidity", "dissolved_oxygen"],
        description="Metrik yang diinginkan. Pilihan: ph, turbidity, dissolved_oxygen, temperature, pollution_index",
    )

    @field_validator("river_name")
    @classmethod
    def river_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("river_name tidak boleh kosong")
        return v


# ═══════════════════════════════════════════════════════════════════
# MODULE IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════

class WaterQualitySensor(PemaliModuleV2):
    """
    Sensor kualitas air real-time untuk sungai di Bali.

    Contoh kanonik: tunjukkan SEMUA best practice pengembangan modul PEMALI.

    Lifecycle:
        1. setup()    → inisialisasi koneksi (dipanggil sekali oleh registry)
        2. execute()  → ambil data dari API, return ModuleOutput terstruktur
        3. teardown() → cleanup koneksi saat shutdown
    """

    # ── METADATA (wajib override via @property) ────────────────

    @property
    def name(self) -> str:
        return "water_quality_sensor"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return (
            "Mengambil data kualitas air real-time dari sensor DAS Bali. "
            "Output mencakup pH, turbidity, dissolved oxygen, suhu, dan indeks "
            "pencemaran. Gunakan untuk audit kualitas air periodik oleh water_agent."
        )

    @property
    def tags(self) -> List[str]:
        # Tag menentukan agent mana yang boleh panggil modul ini.
        # Lihat MODULE_TEMPLATE.md untuk daftar lengkap.
        return ["water", "environment"]

    @property
    def depends_on(self) -> List[str]:
        # Kalau modul ini butuh output dari modul lain, sebutkan di sini.
        # Contoh: ["geo_lookup"] — artinya geo_lookup harus selesai dulu.
        return []

    @property
    def input_schema(self):
        return WaterQualityInput

    @property
    def output_example(self) -> Dict[str, Any]:
        return {
            "status": 200,
            "data": {
                "river_name": "Tukad Ayung",
                "ph": 7.2,
                "turbidity_ntu": 12.4,
                "dissolved_oxygen_mg_l": 6.1,
                "temperature_c": 27.3,
                "pollution_index": "light",
                "sample_timestamp": "2026-05-15T08:00:00Z",
            },
            "agent_hint": (
                "Kualitas air Tukad Ayung baik. pH 7.2, turbidity 12.4 NTU (batas aman 25), "
                "DO 6.1 mg/L. Indeks pencemaran ringan. Tidak ada anomali yang perlu "
                "tindakan segera. Rekomendasi: audit rutin bulan depan untuk track tren."
            ),
            "thk_alignment": {
                "parahyangan": "Data kualitas air dikumpulkan langsung dari sensor tanpa modifikasi — mewakili kondisi asli",
                "pawongan": "Hasil pantauan dapat diakses Dinas Lingkungan Hidup Bali dan masyarakat untuk transparansi",
                "palemahan": "Monitoring rutin mencegah pencemaran sungai yang tidak terdeteksi — menjaga ekosistem air Bali",
            },
        }

    # ── LIFECYCLE HOOKS ────────────────────────────────────────

    async def setup(self, context: Dict[str, Any]) -> None:
        """
        Inisialisasi resource yang dipakai berulang.

        Dipanggil SEKALI oleh registry saat modul pertama kali di-load.
        Jangan taruh resource mahal (DB connection, HTTP session) di __init__ —
        taruh di sini.
        """
        self._session_initialized = True
        # Contoh nyata:
        # self._http = aiohttp.ClientSession(
        #     timeout=aiohttp.ClientTimeout(total=30),
        #     headers={"Authorization": f"Bearer {os.environ['WATER_API_KEY']}"}
        # )

    async def teardown(self, context: Dict[str, Any]) -> None:
        """
        Bersihkan resource.

        Dipanggil SEKALI saat sistem shutdown atau modul di-unload.
        """
        # Contoh nyata:
        # await self._http.close()
        self._session_initialized = False

    # ── CORE LOGIC ─────────────────────────────────────────────

    async def execute(
        self,
        params: WaterQualityInput,
        context: Dict[str, Any],
    ) -> ModuleOutput:
        """
        Ambil data kualitas air dari API dan kembalikan ModuleOutput terstruktur.

        Return value WAJIB mengandung:
        - status (200, 400, 500, dll)
        - data (raw payload)
        - agent_hint (narasi untuk LLM)
        - thk_alignment (Tri Hita Karana)
        """
        start_ms = self._now_ms()

        try:
            # ── Simulasi fetch data ──
            # Ganti bagian ini dengan panggilan API/DB sesungguhnya.
            # Contoh:
            #     async with self._http.get(
            #         f"https://api.waterdata.bali.go.id/rivers/{params.river_name}",
            #         params={"date": params.sample_date, "metrics": ",".join(params.metrics)}
            #     ) as resp:
            #         raw = await resp.json()
            await asyncio.sleep(1.2)

            water_data = self._simulate_sensor_readings(
                params.river_name, params.metrics
            )

            # ── Tentukan anomali ──
            anomaly = self._detect_anomaly(water_data)

            # ── Bangun agent_hint ──
            agent_hint = self._build_agent_hint(
                params.river_name, water_data, anomaly
            )

            # ── Return sukses ──
            execution_ms = round(self._now_ms() - start_ms, 2)
            water_data["execution_ms"] = execution_ms

            return ModuleOutput(
                status=200,
                data=water_data,
                agent_hint=agent_hint,
                thk_alignment=THKPresets.environmental_sensor(
                    "Water Quality Sensor", params.river_name
                ),
            )

        except ValueError as e:
            # Error parameter — agent bisa self-correct
            execution_ms = round(self._now_ms() - start_ms, 2)
            return ModuleOutput(
                status=400,
                data={"execution_ms": execution_ms},
                error_msg=str(e),
                agent_hint=(
                    f"Parameter tidak valid untuk sungai '{params.river_name}'. "
                    f"Pesan: {e}. Coba periksa ejaan nama sungai atau format tanggal."
                ),
            )

        except asyncio.TimeoutError:
            execution_ms = round(self._now_ms() - start_ms, 2)
            return ModuleOutput(
                status=408,
                data={"execution_ms": execution_ms},
                error_msg="Timeout: API tidak merespons dalam 30 detik.",
                agent_hint=(
                    f"Timeout saat fetch data untuk '{params.river_name}'. "
                    f"API eksternal lambat. Coba lagi dengan timeout lebih besar atau periksa status API."
                ),
            )

        except Exception as e:
            execution_ms = round(self._now_ms() - start_ms, 2)
            return ModuleOutput(
                status=500,
                data={"execution_ms": execution_ms},
                error_msg=f"Unexpected: {type(e).__name__}: {e}",
                agent_hint=(
                    f"Error tak terduga saat ambil data '{params.river_name}'. "
                    f"Jangan retry — laporkan ke tim dengan trace: {type(e).__name__}."
                ),
            )

    # ── INTERNAL HELPERS ───────────────────────────────────────

    def _simulate_sensor_readings(
        self, river_name: str, metrics: List[str]
    ) -> Dict[str, Any]:
        """Simulasi pembacaan sensor. GANTI dengan API call sesungguhnya."""
        readings: Dict[str, Any] = {
            "river_name": river_name,
            "sample_timestamp": "2026-05-15T08:00:00Z",
        }

        metric_generators = {
            "ph": lambda: round(random.uniform(6.0, 8.5), 1),
            "turbidity": lambda: round(random.uniform(1.0, 200.0), 1),
            "dissolved_oxygen": lambda: round(random.uniform(2.0, 10.0), 1),
            "temperature": lambda: round(random.uniform(22.0, 32.0), 1),
            "pollution_index": lambda: random.choice(["clean", "light", "moderate", "heavy"]),
        }

        for metric in metrics:
            if metric in metric_generators:
                readings[metric] = metric_generators[metric]()

        return readings

    def _detect_anomaly(self, data: Dict[str, Any]) -> Optional[str]:
        """Deteksi anomali berdasarkan threshold lingkungan."""
        ph = data.get("ph")
        turbidity = data.get("turbidity")
        do = data.get("dissolved_oxygen")

        issues = []
        if ph is not None and (ph < 6.0 or ph > 8.5):
            issues.append(f"pH abnormal ({ph})")
        if turbidity is not None and turbidity > 25:
            issues.append(f"turbidity tinggi ({turbidity} NTU)")
        if do is not None and do < 4.0:
            issues.append(f"dissolved oxygen rendah ({do} mg/L)")

        return "; ".join(issues) if issues else None

    def _build_agent_hint(
        self, river_name: str, data: Dict[str, Any], anomaly: Optional[str]
    ) -> str:
        """Bangun agent_hint yang informatif untuk AI agent."""

        metrics_str = ", ".join(
            f"{k}={v}" for k, v in data.items()
            if k not in ("river_name", "sample_timestamp", "execution_ms")
        )

        if anomaly:
            return (
                f"ANOMALI terdeteksi di {river_name}! {anomaly}. "
                f"Data: {metrics_str}. "
                f"Rekomendasi: cross-check dengan parameter lingkungan lain "
                f"dan pertimbangkan investigasi lapangan."
            )
        else:
            return (
                f"Kualitas air {river_name} dalam batas normal. "
                f"Data: {metrics_str}. "
                f"Tidak ada anomali. Rekomendasi: jadwalkan audit rutin "
                f"bulan depan untuk monitor tren."
            )
