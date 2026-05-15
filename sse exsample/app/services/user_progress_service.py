"""
User Progress Service
=====================
Track user progress: streak, level, stats.

Fitur:
1. Streak tracking (berapa hari berturut-turut belajar)
2. Level progress (total XP, level, progress bar)
3. User stats (semua info penting dalam satu view)

Cara pakai:
    from user_progress_service import UserProgress
    
    # Hitung level dari total XP
    result = UserProgress.hitung_level(7500)
    print(result)
    # Output: {'level': 2, 'xp_di_level': 2500, ...}
    
    # Update streak (cek apakah hari ini update atau reset)
    result = UserProgress.update_streak(last_activity_date, today)
    print(result)
    # Output: {'streak': None, 'status': 'naik'}
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, Tuple


class UserProgress:
    """
    Mengelola user progress: level, XP, streak, stats.
    """
    
    XP_PER_LEVEL = 5000
    
    # ========================================================================
    # LEVEL & XP CALCULATION
    # ========================================================================
    
    @staticmethod
    def hitung_level(total_xp: int) -> Dict:
        """
        Hitung level user dari total XP.
        
        Setiap level = 5000 XP
        
        INPUT:
        - total_xp: total XP yang sudah terkumpul
        
        OUTPUT:
        Dict dengan:
        - level: level berapa
        - xp_di_level_ini: XP di level sekarang
        - xp_butuh: 5000 (untuk setiap level)
        - xp_kurang: masih butuh berapa XP sampai naik level
        - persen_progress: progress 0-100%
        - nama_level: nama tier level
        
        Contoh:
        - total_xp=7500 → level 2, xp_di_level=2500, xp_kurang=2500, progress=50%
        """
        level = (total_xp // UserProgress.XP_PER_LEVEL) + 1
        xp_di_level = total_xp % UserProgress.XP_PER_LEVEL
        xp_kurang = UserProgress.XP_PER_LEVEL - xp_di_level
        persen = (xp_di_level / UserProgress.XP_PER_LEVEL) * 100
        
        # Nama tier level
        if 1 <= level <= 10:
            nama = "Pelajar Pemula 🌱"
        elif 11 <= level <= 20:
            nama = "Pelajar Lanjut 🌿"
        elif 21 <= level <= 30:
            nama = "Pelajar Master 🌳"
        else:
            nama = "Legenda 👑"
        
        return {
            "level": level,
            "xp_di_level_ini": xp_di_level,
            "xp_butuh_per_level": UserProgress.XP_PER_LEVEL,
            "xp_kurang": xp_kurang,
            "persen_progress": round(persen, 1),
            "nama_level": nama
        }
    
    # ========================================================================
    # STREAK MANAGEMENT
    # ========================================================================
    
    @staticmethod
    def update_streak(
        terakhir_aktif: Optional[date],
        hari_ini: date
    ) -> Dict:
        """
        Update streak — cek apakah hari ini streak naik, reset, atau sama hari.
        
        Logika:
        - Sama hari (selisih 0): streak gak berubah
        - Beda 1 hari: streak naik 1
        - Beda > 1 hari: streak reset jadi 1
        - None (user baru): streak mulai dari 1
        
        INPUT:
        - terakhir_aktif: date terakhir user aktif (atau None jika baru)
        - hari_ini: date hari ini
        
        OUTPUT:
        Dict dengan:
        - streak: nilai streak baru (atau None jika gak berubah)
        - status: 'baru' / 'naik' / 'sama_hari' / 'reset'
        - deskripsi: penjelasan apa yang terjadi
        
        Contoh:
        - Hari ini user aktif lagi (beda 1 hari) → {'streak': None, 'status': 'naik'}
        - Sama hari (refresh page): {'streak': None, 'status': 'sama_hari'}
        - User baru: {'streak': 1, 'status': 'baru'}
        """
        
        if terakhir_aktif is None:
            # User baru
            return {
                "streak": 1,
                "status": "baru",
                "deskripsi": "User baru, streak mulai dari 1"
            }
        
        # Hitung selisih hari
        selisih = (hari_ini - terakhir_aktif).days
        
        if selisih == 0:
            # Sama hari
            return {
                "streak": None,
                "status": "sama_hari",
                "deskripsi": "Refresh page hari yang sama, streak tidak berubah"
            }
        elif selisih == 1:
            # Beda 1 hari → streak naik!
            return {
                "streak": None,
                "status": "naik",
                "deskripsi": f"Aktif lagi setelah 1 hari, streak naik 1 hari!"
            }
        else:
            # Beda > 1 hari → reset
            return {
                "streak": 1,
                "status": "reset",
                "deskripsi": f"Lupa belajar {selisih} hari, streak reset jadi 1 😢"
            }
    
    @staticmethod
    def get_badge_milestone(streak: int) -> Optional[Dict]:
        """
        Cek apakah streak sudah mencapai milestone (dapat badge).
        
        Milestones:
        - 7 hari: 🔥 7-Day Warrior
        - 14 hari: 💪 2-Week Champion
        - 30 hari: 🏆 Monthly Legend
        - 100 hari: 👑 Centennial King
        
        INPUT:
        - streak: berapa hari streak saat ini
        
        OUTPUT:
        Dict dengan badge info, atau None jika belum milestone
        
        Contoh:
        - streak=7 → {'emoji': '🔥', 'name': '7-Day Warrior', 'xp_bonus': 50}
        - streak=6 → None
        """
        milestones = {
            7: {"emoji": "🔥", "name": "7-Day Warrior", "xp_bonus": 50},
            14: {"emoji": "💪", "name": "2-Week Champion", "xp_bonus": 100},
            30: {"emoji": "🏆", "name": "Monthly Legend", "xp_bonus": 200},
            100: {"emoji": "👑", "name": "Centennial King", "xp_bonus": 500}
        }
        
        return milestones.get(streak, None)
    
    # ========================================================================
    # USER STATS
    # ========================================================================
    
    @staticmethod
    def build_user_stats(
        total_xp: int,
        current_streak: int,
        longest_streak: int,
        total_chats: int = 0,
        total_reviews: int = 0
    ) -> Dict:
        """
        Build complete user stats untuk dashboard.
        
        INPUT:
        - total_xp: total XP yang sudah dikumpulin
        - current_streak: streak saat ini
        - longest_streak: streak terbaik ever
        - total_chats: berapa chat session (optional)
        - total_reviews: berapa review (optional)
        
        OUTPUT:
        Dict lengkap dengan semua stats user
        
        Contoh output:
        {
            'level': 2,
            'total_xp': 7500,
            'nama_level': 'Pelajar Lanjut',
            'current_streak': 10,
            'longest_streak': 15,
            'xp_to_next_level': 2500,
            'progress_persen': 50.0,
            'status_message': 'Semangat! Tinggal 2500 XP lagi...'
        }
        """
        level_info = UserProgress.hitung_level(total_xp)
        
        # Tentukan status message
        if level_info["persen_progress"] < 25:
            status = "Mulai kuat! 💪"
        elif level_info["persen_progress"] < 50:
            status = "Semangat! Tinggal tengah jalan... 🚀"
        elif level_info["persen_progress"] < 75:
            status = "Hampir naik level! Lanjutkan! 🔥"
        else:
            status = "Tinggal sedikit lagi! 🎯"
        
        return {
            "level": level_info["level"],
            "nama_level": level_info["nama_level"],
            "total_xp": total_xp,
            "xp_di_level": level_info["xp_di_level_ini"],
            "xp_kurang": level_info["xp_kurang"],
            "progress_persen": level_info["persen_progress"],
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_chats": total_chats,
            "total_reviews": total_reviews,
            "status_message": status,
            "milestones_terdekat": UserProgress._hitung_milestone_terdekat(current_streak)
        }
    
    @staticmethod
    def _hitung_milestone_terdekat(streak: int) -> str:
        """
        Hitung milestone terdekat dan kasih pesan motivasi.
        
        Contoh:
        - streak=5 → "2 hari lagi! 🔥 7-Day Warrior badge"
        - streak=28 → "2 hari lagi! 🏆 Monthly Legend badge"
        """
        milestones = [7, 14, 30, 100]
        
        for m in milestones:
            if streak < m:
                sisa = m - streak
                badge_info = UserProgress.get_badge_milestone(m)
                if badge_info:
                    return f"{sisa} hari lagi! {badge_info['emoji']} {badge_info['name']} badge"
                return f"{sisa} hari lagi untuk milestone {m} hari"
        
        return "Sudah mencapai semua milestone! 👑"
    
    # ========================================================================
    # UTILITY
    # ========================================================================
    
    @staticmethod
    def hitung_hari_sejak_terakhir_aktif(terakhir_aktif: Optional[date]) -> int:
        """
        Hitung berapa hari sejak user terakhir aktif.
        
        INPUT:
        - terakhir_aktif: date terakhir aktif (atau None)
        
        OUTPUT:
        - jumlah hari (0 = hari ini, 1 = kemarin, dst)
        
        Gampang:
        - None → -1 (never active)
        - Hari ini → 0
        - Kemarin → 1
        """
        if terakhir_aktif is None:
            return -1
        
        hari_ini = date.today()
        selisih = (hari_ini - terakhir_aktif).days
        return max(0, selisih)


# ============================================================================
# CONTOH PEMAKAIAN
# ============================================================================

if __name__ == "__main__":
    print("=== TEST USER PROGRESS ===\n")
    
    # Skenario 1: User dengan 7500 XP, streak 10 hari
    print("Skenario 1: Level user")
    level = UserProgress.hitung_level(7500)
    print(f"  Level: {level['level']} ({level['nama_level']})")
    print(f"  Progress: {level['persen_progress']}%")
    print(f"  Kurang: {level['xp_kurang']} XP\n")
    
    # Skenario 2: Update streak
    print("Skenario 2: Update streak")
    from datetime import date, timedelta
    
    kemarin = date.today() - timedelta(days=1)
    hari_ini = date.today()
    
    result = UserProgress.update_streak(kemarin, hari_ini)
    print(f"  Status: {result['status']}")
    print(f"  Deskripsi: {result['deskripsi']}\n")
    
    # Skenario 3: Badge milestone
    print("Skenario 3: Streak milestone")
    badge = UserProgress.get_badge_milestone(7)
    print(f"  Badge 7 hari: {badge['emoji']} {badge['name']}")
    print(f"  Bonus XP: {badge['xp_bonus']}\n")
    
    # Skenario 4: Full user stats
    print("Skenario 4: Full user stats")
    stats = UserProgress.build_user_stats(
        total_xp=7500,
        current_streak=10,
        longest_streak=15,
        total_chats=42,
        total_reviews=23
    )
    print(f"  Level: {stats['nama_level']}")
    print(f"  Streak: {stats['current_streak']} (best: {stats['longest_streak']})")
    print(f"  Status: {stats['status_message']}")
    print(f"  Milestone terdekat: {stats['milestones_terdekat']}\n")