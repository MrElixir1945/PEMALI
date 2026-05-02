# Simulasi data yang realistis sesuai skenario PDF (tanpa memanggil external API)

MOCK_REGIONS = ["bedugul", "ubud", "buleleng"]

# Data Satelit (NDVI - Normalized Difference Vegetation Index)
MOCK_SATELLITE_DATA = {
    "bedugul": {
        "ndvi_current": 0.528,
        "ndvi_baseline": 0.600,
        "change_pct": -12.0,  # Sesuai PDF: penurunan 12%
        "status": "DEFORESTASI_SIGNIFIKAN",
        "history": [
            {"month": "Nov", "ndvi": 0.600},
            {"month": "Des", "ndvi": 0.585},
            {"month": "Jan", "ndvi": 0.570},
            {"month": "Feb", "ndvi": 0.552},
            {"month": "Mar", "ndvi": 0.540},
            {"month": "Apr", "ndvi": 0.528},
        ]
    },
    "ubud": {
        "ndvi_current": 0.450,
        "ndvi_baseline": 0.465,
        "change_pct": -3.2,
        "status": "ALUH_FUNGSI_RINGAN",
        "history": [
            {"month": "Nov", "ndvi": 0.465},
            {"month": "Des", "ndvi": 0.460},
            {"month": "Jan", "ndvi": 0.455},
            {"month": "Feb", "ndvi": 0.455},
            {"month": "Mar", "ndvi": 0.452},
            {"month": "Apr", "ndvi": 0.450},
        ]
    },
    "buleleng": {
        "ndvi_current": 0.680,
        "ndvi_baseline": 0.675,
        "change_pct": 0.7,
        "status": "STABIL",
        "history": [
            {"month": "Nov", "ndvi": 0.675},
            {"month": "Des", "ndvi": 0.678},
            {"month": "Jan", "ndvi": 0.680},
            {"month": "Feb", "ndvi": 0.675},
            {"month": "Mar", "ndvi": 0.678},
            {"month": "Apr", "ndvi": 0.680},
        ]
    }
}

# Data OSINT (Media Sosial & Kesadaran Publik)
MOCK_OSINT_DATA = {
    "bedugul": {
        "total_posts": 1250,
        "env_mentions": 100,  # 8% sesuai PDF
        "awareness_score": 8, 
        "top_keywords": ["wisata", "liburan", "danau beratan", "foto", "macet"] # noise tinggi
    },
    "ubud": {
        "total_posts": 3400,
        "env_mentions": 1428, # ~42%
        "awareness_score": 42,
        "top_keywords": ["sawah", "alih fungsi", "yoga", "villa", "macet"]
    },
    "buleleng": {
        "total_posts": 800,
        "env_mentions": 480, # 60%
        "awareness_score": 60,
        "top_keywords": ["pantai", "bersih", "mangrove", "konservasi", "lumba-lumba"]
    }
}

# Parameter Tri Hita Karana (THK)
THK_PARAMETERS = {
    "parahyangan": {
        "label": "Keseimbangan Manusia–Alam Sakral",
        "ndvi_threshold": -8.0,
        "fail_msg": "Kawasan sakral/hutan adat berpotensi terdampak deforestasi serius."
    },
    "pawongan": {
        "label": "Keseimbangan Antar Manusia",
        "awareness_threshold": 20,
        "fail_msg": "Komunitas tidak merespons secara kolektif — gap sosial terdeteksi."
    },
    "palemahan": {
        "label": "Keseimbangan Manusia–Lingkungan Fisik",
        "ndvi_threshold": -5.0,
        "fail_msg": "Degradasi ekosistem fisik signifikan. Alih fungsi lahan tinggi."
    }
}
