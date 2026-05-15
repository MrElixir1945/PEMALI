"""
SM-2 Service
============
Algoritma SM-2 untuk hitung interval review berikutnya.
Simpel dan proven (30+ tahun).

Cara pakai:
    from sm2_service import SM2
    
    # User bilang "mudah" (rating 4) untuk pesan ini
    hasil = SM2.hitung_review(rating=4, repetisi_sebelumnya=0)
    print(hasil)
    # Output: {'hari_berikutnya': 1, 'ease_factor': 2.5}
"""

from datetime import datetime, timedelta
from typing import Dict


class SM2:
    """
    SM-2 Algorithm — Super Memory 2
    
    Hitung kapan harus review ulang berdasarkan rating user.
    Rating: 1 (susah sekali) sampai 5 (mudah sekali)
    """
    
    # Nilai easiness factor range
    MIN_EASE = 1.3
    MAX_EASE = 2.5
    
    @staticmethod
    def hitung_review(
        rating: int,
        ease_factor_sekarang: float = 2.5,
        repetisi_sebelumnya: int = 0
    ) -> Dict:
        """
        Hitung interval review berikutnya + ease factor baru.
        
        INPUT:
        - rating: User bilang mudah/susah? (1-5)
            1 = sangat susah
            2 = susah
            3 = lumayan
            4 = mudah
            5 = sangat mudah
        - ease_factor_sekarang: nilai sebelumnya (default 2.5)
        - repetisi_sebelumnya: berapa kali sudah di-review
        
        OUTPUT:
        Dict dengan:
        - hari_berikutnya: berapa hari sampai review lagi
        - ease_factor_baru: nilai baru untuk next review
        - deskripsi: penjelasan apa yg terjadi
        """
        
        # Step 1: Hitung ease factor baru pakai rumus SM-2
        # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        # Dimana q = rating (quality)
        
        ease_baru = ease_factor_sekarang + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))
        
        # Batasi ease factor antara 1.3 dan 2.5
        ease_baru = max(SM2.MIN_EASE, min(SM2.MAX_EASE, ease_baru))
        
        # Step 2: Hitung hari berikutnya pakai rumus:
        # Repetisi 1: 1 hari
        # Repetisi 2: 3 hari
        # Repetisi n: I(n-1) * EF
        
        if repetisi_sebelumnya == 0:
            # Pertama kali review
            hari_berikutnya = 1
            deskripsi = "Pertama kali review → review ulang besok"
        elif repetisi_sebelumnya == 1:
            # Kedua kalinya
            hari_berikutnya = 3
            deskripsi = "Review kedua → tunggu 3 hari"
        else:
            # Ketiga kalinya dan seterusnya
            hari_berikutnya = int(3 * (ease_baru / 2.5) * (repetisi_sebelumnya - 1))
            hari_berikutnya = max(1, hari_berikutnya)  # Minimal 1 hari
            deskripsi = f"Review ke-{repetisi_sebelumnya + 1} → tunggu {hari_berikutnya} hari"
        
        # Step 3: Hitung tanggal review berikutnya
        hari_ini = datetime.now()
        tanggal_berikutnya = hari_ini + timedelta(days=hari_berikutnya)
        
        return {
            "hari_berikutnya": hari_berikutnya,
            "ease_factor_baru": round(ease_baru, 2),
            "tanggal_review_berikutnya": tanggal_berikutnya,
            "deskripsi": deskripsi,
            "rating_diberikan": rating
        }
    
    @staticmethod
    def mapkan_rating_ke_box(hari_interval: int) -> str:
        """
        Mapkan hari interval ke Leitner box (untuk UI).
        
        Gampang aja:
        - < 1 hari → Box 1 (Urgent)
        - < 3 hari → Box 2
        - < 7 hari → Box 3
        - < 14 hari → Box 4
        - >= 14 hari → Box 5 (Mastery)
        """
        if hari_interval < 1:
            return "Box 1 - Urgent 🔴"
        elif hari_interval < 3:
            return "Box 2 - Perlu Review 🟠"
        elif hari_interval < 7:
            return "Box 3 - Consolidating 🟡"
        elif hari_interval < 14:
            return "Box 4 - Remembered 🟢"
        else:
            return "Box 5 - Mastery ✅"


# ============================================================================
# CONTOH PEMAKAIAN
# ============================================================================

if __name__ == "__main__":
    print("=== TEST SM-2 ALGORITHM ===\n")
    
    # Skenario 1: User bilang "mudah" (rating 4) saat pertama kali review
    print("Skenario 1: Rating 4 (mudah), pertama kali")
    hasil1 = SM2.hitung_review(rating=4, repetisi_sebelumnya=0)
    print(f"  Ease factor baru: {hasil1['ease_factor_baru']}")
    print(f"  Hari berikutnya: {hasil1['hari_berikutnya']} hari")
    print(f"  Box: {SM2.mapkan_rating_ke_box(hasil1['hari_berikutnya'])}\n")
    
    # Skenario 2: User bilang "susah" (rating 2) saat kedua kali review
    print("Skenario 2: Rating 2 (susah), kedua kali")
    hasil2 = SM2.hitung_review(
        rating=2, 
        ease_factor_sekarang=2.5, 
        repetisi_sebelumnya=1
    )
    print(f"  Ease factor baru: {hasil2['ease_factor_baru']}")
    print(f"  Hari berikutnya: {hasil2['hari_berikutnya']} hari")
    print(f"  Box: {SM2.mapkan_rating_ke_box(hasil2['hari_berikutnya'])}\n")
    
    # Skenario 3: User bilang "sangat mudah" (rating 5) saat ketiga kali
    print("Skenario 3: Rating 5 (sangat mudah), ketiga kali")
    hasil3 = SM2.hitung_review(
        rating=5, 
        ease_factor_sekarang=2.3, 
        repetisi_sebelumnya=2
    )
    print(f"  Ease factor baru: {hasil3['ease_factor_baru']}")
    print(f"  Hari berikutnya: {hasil3['hari_berikutnya']} hari")
    print(f"  Box: {SM2.mapkan_rating_ke_box(hasil3['hari_berikutnya'])}\n")