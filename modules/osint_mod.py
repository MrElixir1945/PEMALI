import asyncio
from typing import Dict, Any
from core.base_module import PemaliModule, ModuleOutput


class OsintModule(PemaliModule):
    """
    Modul Connector V2 untuk pengumpulan intelijen sumber terbuka (OSINT).
    Mengagregasi berita media, laporan warga, sentimen publik, dan metadata
    perizinan terkait isu lingkungan & tata ruang di area target.
    """

    @property
    def manifest(self) -> Dict[str, Any]:
        return {
            "name": "osint_intel",
            "description": (
                "Gunakan tool ini untuk mengumpulkan data intelijen sumber terbuka (OSINT) "
                "terkait suatu lokasi: berita media lokal/nasional, laporan warga, "
                "sentimen komunitas, dan informasi perizinan. Wajib dipanggil ketika "
                "pengguna meminta investigasi sosial, audit komunitas, cek reputasi lokasi, "
                "atau ketika diperlukan konteks sosial-politik untuk melengkapi audit lingkungan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Kata kunci pencarian untuk OSINT. Bisa nama lokasi, proyek, "
                            "atau isu spesifik. Contoh: 'Subak Canggu alih fungsi lahan' "
                            "atau 'pembangunan hotel Ubud izin lingkungan'."
                        )
                    },
                    "lokasi": {
                        "type": "string",
                        "description": (
                            "Nama lokasi/daerah yang menjadi fokus investigasi. "
                            "Contoh: 'Canggu', 'Ubud', 'Seminyak'."
                        )
                    },
                    "max_artikel": {
                        "type": "integer",
                        "description": "Jumlah maksimum artikel berita yang diambil. Default 10, maksimum 25."
                    }
                },
                "required": ["query"]
            }
        }

    async def execute(self, params: Dict[str, Any], session_id: str = None) -> ModuleOutput:
        """
        Menjalankan pengumpulan OSINT: agregasi berita, analisis sentimen,
        dan identifikasi isu-isu kritis yang relevan dengan query dan lokasi target.
        """
        try:
            query = params.get("query", "")
            lokasi = params.get("lokasi", "Bali")
            max_artikel = min(int(params.get("max_artikel", 10)), 25)

            # === SIMULASI / PLACEHOLDER NEWS API CALL ===
            # Di produksi, blok ini diganti dengan:
            #   import newsapi  /  requests ke NewsAPI.org / scraper
            #   response = newsapi.get_everything(q=query, language="id", page_size=max_artikel)
            # ============================================
            await asyncio.sleep(0.6)  # Simulasi I/O latency

            # Data simulasi hasil OSINT
            artikel_ditemukan = [
                {
                    "judul": f"Konversi Lahan Sawah di {lokasi} Meningkat 15% Tahun Ini",
                    "sumber": "Bali Post",
                    "tanggal": "2026-04-28",
                    "sentimen": "negatif",
                    "url": "https://balipost.com/artikel/simulasi-1"
                },
                {
                    "judul": f"Warga {lokasi} Tolak Pembangunan Resort di Kawasan Subak",
                    "sumber": "Kompas Regional",
                    "tanggal": "2026-04-21",
                    "sentimen": "negatif",
                    "url": "https://kompas.com/artikel/simulasi-2"
                },
                {
                    "judul": f"Pemkab Pastikan Izin Lingkungan Ketat di {lokasi}",
                    "sumber": "Tribun Bali",
                    "tanggal": "2026-04-15",
                    "sentimen": "netral",
                    "url": "https://tribun.com/artikel/simulasi-3"
                }
            ]

            total_artikel = len(artikel_ditemukan)
            sentimen_negatif = sum(1 for a in artikel_ditemukan if a["sentimen"] == "negatif")
            sentimen_positif = sum(1 for a in artikel_ditemukan if a["sentimen"] == "positif")
            skor_risiko_sosial = round((sentimen_negatif / total_artikel) * 100) if total_artikel else 0

            # Evaluasi level risiko sosial
            if skor_risiko_sosial >= 60:
                level_isu = "Kritis"
                rekomendasi = "Segera lakukan investigasi lapangan dan koordinasi multipihak."
            elif skor_risiko_sosial >= 30:
                level_isu = "Waspada"
                rekomendasi = "Pantau perkembangan isu dan siapkan dialog komunitas."
            else:
                level_isu = "Normal"
                rekomendasi = "Lanjutkan monitoring berkala."

            return ModuleOutput(
                status="success",
                data={
                    "query": query,
                    "lokasi": lokasi,
                    "total_artikel_ditemukan": total_artikel,
                    "max_diminta": max_artikel,
                    "distribusi_sentimen": {
                        "negatif": sentimen_negatif,
                        "positif": sentimen_positif,
                        "netral": total_artikel - sentimen_negatif - sentimen_positif
                    },
                    "skor_risiko_sosial_pct": skor_risiko_sosial,
                    "level_isu": level_isu,
                    "artikel": artikel_ditemukan,
                    "rekomendasi": rekomendasi
                },
                agent_hint=(
                    f"OSINT untuk '{query}' di {lokasi}: ditemukan {total_artikel} artikel relevan. "
                    f"Tingkat risiko sosial: {skor_risiko_sosial}% ({level_isu}). "
                    f"Sentimen negatif mendominasi ({sentimen_negatif}/{total_artikel} artikel). "
                    f"Temuan kunci: konversi lahan dan resistensi komunitas lokal terdeteksi. "
                    f"{rekomendasi}"
                ),
                thk_alignment="Pawongan"
            )

        except Exception as e:
            return ModuleOutput(
                status="error",
                data={"error_detail": str(e), "query": params.get("query", "unknown")},
                agent_hint=(
                    f"Gagal menjalankan pengumpulan OSINT untuk query '{params.get('query')}'. "
                    "Terjadi kesalahan internal. Periksa koneksi ke sumber data berita."
                ),
                thk_alignment="Pawongan"
            )
