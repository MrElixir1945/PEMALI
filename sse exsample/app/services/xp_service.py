"""
XP Service
==========
Hitung berapa XP yang user dapat, dengan multiplier dinamis.

3 faktor multiplier:
1. Waktu belajar (pagi bonus, malam kurang)
2. Streak (belajar terus-menerus dapat bonus)
3. Kualitas pesan (pesan panjang dapat bonus)

Cara pakai:
    from xp_service import XP
    
    xp = XP.hitung_xp_final(
        base_xp=5,
        jam_sekarang=9,
        hari_streak=10,
        panjang_pesan_kata=400
    )
    print(xp)  # Output: 6 atau 7 (sudah dikali multiplier)
"""

from datetime import datetime
from math import exp


class XP:
    """
    XP Calculator dengan 3 multiplier dinamis.
    Semua dihitung pakai geometric mean supaya balance.
    """
    
    # Base XP per message (bisa adjust)
    BASE_XP_CHAT = 5
    BASE_XP_REVIEW = 10
    
    @staticmethod
    def hitung_multiplier_waktu(jam_sekarang: int) -> float:
        """
        Multiplier berdasarkan jam belajar.
        
        Logika:
        - Pagi (7-12): Fresh brain = 1.2x bonus
        - Siang (12-18): Normal = 1.0x
        - Malam (18-7): Kurang bagus = 0.8x
        
        INPUT:
        - jam_sekarang: jam sekarang (0-23)
        
        OUTPUT:
        - multiplier (0.8 sampai 1.2)
        """
        if 7 <= jam_sekarang < 12:
            return 1.2  # Pagi → brain fresh
        elif 12 <= jam_sekarang < 18:
            return 1.0  # Siang → normal
        else:
            return 0.8  # Malam → kurang ideal
    
    @staticmethod
    def hitung_multiplier_streak(hari_streak: int) -> float:
        """
        Multiplier berdasarkan streak (konsistensi).
        
        Logika:
        - Streak 30+ hari: 1.5x (luar biasa konsisten!)
        - Streak 7-29 hari: 1.2x (bagus)
        - Streak 3-6 hari: 1.1x (lumayan)
        - Streak 0-2 hari: 1.0x (baru mulai)
        
        INPUT:
        - hari_streak: berapa hari berturut-turut belajar
        
        OUTPUT:
        - multiplier (1.0 sampai 1.5)
        """
        if hari_streak >= 30:
            return 1.5
        elif hari_streak >= 7:
            return 1.2
        elif hari_streak >= 3:
            return 1.1
        else:
            return 1.0
    
    @staticmethod
    def hitung_multiplier_kualitas(panjang_pesan_kata: int, ada_followup: bool = False) -> float:
        """
        Multiplier berdasarkan engagement/kualitas.
        
        Logika:
        - Pesan >500 kata: 1.5x (sangat engage)
        - Pesan 200-500 kata: 1.25x (bagus)
        - Pesan 100-200 kata: 1.1x (lumayan)
        - Pesan <100 kata: 1.0x (pendek)
        - Ada follow-up question: +0.2x bonus
        
        INPUT:
        - panjang_pesan_kata: berapa kata dalam reply Armisa
        - ada_followup: user bertanya lanjutan? (bonus)
        
        OUTPUT:
        - multiplier (1.0 sampai 1.7)
        """
        base = 1.0
        
        # Bonus berdasarkan panjang
        if panjang_pesan_kata > 500:
            base = 1.5
        elif panjang_pesan_kata > 200:
            base = 1.25
        elif panjang_pesan_kata > 100:
            base = 1.1
        
        # Bonus follow-up
        if ada_followup:
            base += 0.2
        
        return base
    
    @staticmethod
    def hitung_multiplier_total(
        jam_sekarang: int,
        hari_streak: int,
        panjang_pesan_kata: int,
        ada_followup: bool = False
    ) -> float:
        """
        Gabung semua multiplier pakai geometric mean.
        
        Formula: (a * b * c)^(1/3)
        
        Geometric mean = lebih fair, gak ada yang overpowered.
        
        Contoh:
        - Time: 1.2, Streak: 1.2, Quality: 1.3
        - Hasil: (1.2 * 1.2 * 1.3)^(1/3) ≈ 1.23x
        - Bukan (1.2 + 1.2 + 1.3) / 3 = 1.23x (arithmetic mean)
        
        OUTPUT:
        - total multiplier (0.8 sampai ~1.5)
        """
        mult_waktu = XP.hitung_multiplier_waktu(jam_sekarang)
        mult_streak = XP.hitung_multiplier_streak(hari_streak)
        mult_kualitas = XP.hitung_multiplier_kualitas(panjang_pesan_kata, ada_followup)
        
        # Geometric mean
        total = (mult_waktu * mult_streak * mult_kualitas) ** (1/3)
        
        return round(total, 2)
    
    @staticmethod
    def hitung_xp_final(
        base_xp: int,
        jam_sekarang: int,
        hari_streak: int,
        panjang_pesan_kata: int,
        ada_followup: bool = False
    ) -> int:
        """
        Hitung final XP dengan semua multiplier.
        
        INPUT:
        - base_xp: XP dasar (biasanya 5 atau 10)
        - jam_sekarang: jam berapa sekarang (0-23)
        - hari_streak: berapa hari streak
        - panjang_pesan_kata: panjang reply Armisa
        - ada_followup: user follow-up question?
        
        OUTPUT:
        - final XP (integer, sudah dikali multiplier)
        
        Contoh:
        - base=5, jam=9, streak=10, kata=400
        - mult = 1.23
        - hasil = int(5 * 1.23) = 6 XP
        """
        multiplier = XP.hitung_multiplier_total(
            jam_sekarang, hari_streak, panjang_pesan_kata, ada_followup
        )
        final_xp = int(base_xp * multiplier)
        return final_xp
    
    @staticmethod
    def hitung_level(total_xp: int) -> dict:
        """
        Hitung level user berdasarkan total XP.
        
        Setiap level butuh 5000 XP.
        
        INPUT:
        - total_xp: total XP yang sudah terkumpul
        
        OUTPUT:
        Dict dengan:
        - level: level berapa sekarang
        - xp_di_level_ini: XP yang sudah dapet di level ini
        - xp_butuh: XP total butuh untuk level ini (5000)
        - xp_kurang: XP masih kurang
        - persen_progress: progress 0-100%
        """
        XP_PER_LEVEL = 5000
        
        level = (total_xp // XP_PER_LEVEL) + 1
        xp_di_level = total_xp % XP_PER_LEVEL
        xp_kurang = XP_PER_LEVEL - xp_di_level
        persen = (xp_di_level / XP_PER_LEVEL) * 100
        
        return {
            "level": level,
            "xp_di_level_ini": xp_di_level,
            "xp_butuh_per_level": XP_PER_LEVEL,
            "xp_kurang": xp_kurang,
            "persen_progress": round(persen, 1)
        }
    
    @staticmethod
    def nama_level(level: int) -> str:
        """
        Kasih nama fancy untuk setiap level.
        
        Level 1-10: Pelajar Pemula
        Level 11-20: Pelajar Lanjut
        Level 21-30: Pelajar Master
        Level 30+: Legenda
        """
        if 1 <= level <= 10:
            return "Pelajar Pemula"
        elif 11 <= level <= 20:
            return "Pelajar Lanjut"
        elif 21 <= level <= 30:
            return "Pelajar Master"
        else:
            return "Legenda"


# ============================================================================
# CONTOH PEMAKAIAN
# ============================================================================

if __name__ == "__main__":
    print("=== TEST XP SYSTEM ===\n")
    
    # Skenario 1: User belajar jam 9 pagi, streak 10 hari, reply 400 kata
    print("Skenario 1: Pagi, streak 10, pesan 400 kata")
    xp1 = XP.hitung_xp_final(
        base_xp=5,
        jam_sekarang=9,
        hari_streak=10,
        panjang_pesan_kata=400
    )
    mult1 = XP.hitung_multiplier_total(9, 10, 400)
    print(f"  Multiplier: {mult1}x")
    print(f"  XP gained: {xp1} (dari base 5)\n")
    
    # Skenario 2: User belajar jam 11 malam, streak 2 hari, reply pendek 100 kata
    print("Skenario 2: Malam jam 23, streak 2, pesan 100 kata")
    xp2 = XP.hitung_xp_final(
        base_xp=5,
        jam_sekarang=23,
        hari_streak=2,
        panjang_pesan_kata=100
    )
    mult2 = XP.hitung_multiplier_total(23, 2, 100)
    print(f"  Multiplier: {mult2}x")
    print(f"  XP gained: {xp2} (dari base 5)\n")
    
    # Skenario 3: User 7500 XP total - berapa levelnya?
    print("Skenario 3: Total XP 7500")
    level = XP.hitung_level(7500)
    print(f"  Level: {level['level']} ({XP.nama_level(level['level'])})")
    print(f"  Progress: {level['persen_progress']}%")
    print(f"  Kurang: {level['xp_kurang']} XP\n")