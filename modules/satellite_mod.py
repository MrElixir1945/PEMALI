import asyncio
from typing import Dict, Any
from core.base_module import PemaliModule, ModuleOutput


class SatelliteModule(PemaliModule):
    """
    Modul Connector V2 untuk akuisisi dan interpretasi citra satelit Sentinel-2
    via Google Earth Engine (GEE). Menganalisis vegetasi (NDVI), tutupan lahan,
    dan indikasi alih fungsi lahan pada area Subak atau kawasan hijau Bali.
    """

    @property
    def manifest(self) -> Dict[str, Any]:
        return {
            "name": "satellite_audit",
            "description": (
                "Gunakan tool ini untuk menganalisis kondisi vegetasi dan tutupan lahan "
                "dari citra satelit Sentinel-2. Wajib dipanggil saat pengguna meminta audit "
                "lingkungan, deteksi alih fungsi lahan, analisis sawah/Subak, atau ketika "
                "indeks NDVI dan perubahan tutupan lahan perlu dievaluasi. Input berupa "
                "nama lokasi atau koordinat (latitude/longitude) dan rentang waktu analisis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lokasi": {
                        "type": "string",
                        "description": (
                            "Nama lokasi yang akan dianalisis. "
                            "Contoh: 'Subak Jatiluwih, Tabanan' atau 'Canggu, Badung'."
                        )
                    },
                    "koordinat": {
                        "type": "object",
                        "description": "Koordinat geografis opsional untuk presisi lebih tinggi.",
                        "properties": {
                            "lat": {"type": "number", "description": "Latitude (lintang)."},
                            "lon": {"type": "number", "description": "Longitude (bujur)."}
                        }
                    },
                    "periode_bulan": {
                        "type": "integer",
                        "description": (
                            "Rentang waktu analisis dalam bulan ke belakang dari hari ini. "
                            "Default 6 bulan. Maksimum 24 bulan."
                        )
                    }
                },
                "required": ["lokasi"]
            }
        }

    async def execute(self, params: Dict[str, Any], session_id: str = None) -> ModuleOutput:
        """
        Mengambil dan menganalisis data citra satelit Sentinel-2 untuk lokasi target.
        Menghasilkan metrik NDVI, kerapatan vegetasi, dan indikasi alih fungsi lahan.
        """
        try:
            lokasi = params.get("lokasi", "Lokasi tidak diketahui")
            koordinat = params.get("koordinat", {})
            periode_bulan = min(int(params.get("periode_bulan", 6)), 24)

            # === SIMULASI / PLACEHOLDER GEE CALL ===
            # Di produksi, blok ini diganti dengan:
            #   import ee
            #   ee.Initialize(credentials)
            #   collection = ee.ImageCollection("COPERNICUS/S2_SR") ...
            # ==========================================
            await asyncio.sleep(0.8)  # Simulasi I/O latency GEE

            # Data hasil analisis citra (nilai simulasi)
            ndvi_rata = 0.41
            ndvi_tren = "menurun"
            luas_vegetasi_ha = 127.3
            luas_terbangun_ha = 89.7
            perubahan_lahan_pct = 12.4
            cloud_cover_pct = 8.2

            # Evaluasi status berdasarkan threshold NDVI
            if ndvi_rata >= 0.6:
                status_vegetasi = "Sehat"
                level_risiko = "Rendah"
            elif ndvi_rata >= 0.35:
                status_vegetasi = "Tertekan"
                level_risiko = "Sedang"
            else:
                status_vegetasi = "Kritis"
                level_risiko = "Tinggi"

            # Susun hint berdasarkan kondisi deteksi
            if perubahan_lahan_pct > 10:
                hint = (
                    f"PERINGATAN: Analisis Sentinel-2 di {lokasi} menunjukkan NDVI rata-rata "
                    f"{ndvi_rata} (tren {ndvi_tren}) dengan indikasi alih fungsi lahan sebesar "
                    f"{perubahan_lahan_pct}% dalam {periode_bulan} bulan terakhir. "
                    f"Luas area terbangun baru ~{luas_terbangun_ha} ha. "
                    f"Status vegetasi: {status_vegetasi} — risiko ekologi {level_risiko}. "
                    "Direkomendasikan inspeksi lapangan dan koordinasi dengan Dinas LHK."
                )
            else:
                hint = (
                    f"Analisis citra satelit Sentinel-2 di {lokasi}: NDVI rata-rata {ndvi_rata} "
                    f"({status_vegetasi}). Tidak ada indikasi signifikan alih fungsi lahan dalam "
                    f"{periode_bulan} bulan terakhir. Vegetasi relatif terjaga."
                )

            return ModuleOutput(
                status="success",
                data={
                    "lokasi": lokasi,
                    "koordinat": koordinat,
                    "periode_analisis_bulan": periode_bulan,
                    "sensor": "Sentinel-2 MSI (via Google Earth Engine)",
                    "ndvi": {
                        "rata_rata": ndvi_rata,
                        "tren": ndvi_tren,
                        "status": status_vegetasi,
                        "level_risiko": level_risiko
                    },
                    "tutupan_lahan": {
                        "vegetasi_ha": luas_vegetasi_ha,
                        "terbangun_ha": luas_terbangun_ha,
                        "perubahan_pct": perubahan_lahan_pct
                    },
                    "kualitas_citra": {
                        "cloud_cover_pct": cloud_cover_pct
                    }
                },
                agent_hint=hint,
                thk_alignment="Palemahan"
            )

        except Exception as e:
            return ModuleOutput(
                status="error",
                data={"error_detail": str(e), "lokasi": params.get("lokasi", "unknown")},
                agent_hint=(
                    f"Gagal mengambil data satelit untuk lokasi '{params.get('lokasi')}'. "
                    "Terjadi kesalahan saat menghubungi layanan Google Earth Engine. "
                    "Coba periksa koneksi atau kredensial GEE."
                ),
                thk_alignment="Palemahan"
            )
