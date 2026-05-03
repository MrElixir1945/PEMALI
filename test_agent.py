import asyncio
from core.orchestrator import PemaliOrchestrator

async def main():
    # 1. Tentukan session_id unik untuk audit ini
    session_id = "audit-ubud-001"
    
    # 2. Inisialisasi Orchestrator (The Brain)
    # Pastikan model name sesuai dengan yang tersedia di OpenRouter
    agent = PemaliOrchestrator(session_id=session_id)
    
    # 3. Berikan instruksi awal
    # Prompt ini didesain untuk memicu ReAct loop secara penuh
    prompt = (
        "Lakukan audit komprehensif di Ubud sekarang. Langkah yang harus dilakukan:\n"
        "1. Ambil data citra satelit terbaru.\n"
        "2. Verifikasi legalitas spasial dan zonasi wilayah tersebut.\n"
        "3. Analisis tingkat kerusakan lingkungan menggunakan data satelit.\n"
        "4. Tulis laporan audit final ke database.\n"
        "5. Jadwalkan pemeriksaan ulang otomatis 1 menit dari sekarang untuk memantau aktivitas mencurigakan."
    )
    
    print(f"[*] Starting Agent Session: {session_id}")
    print(f"[*] Prompt: {prompt}\n")
    
    try:
        # 4. Jalankan ReAct Loop
        final_response = await agent.run(prompt)
        
        print("\n" + "="*50)
        print("FINAL AGENT RESPONSE:")
        print("="*50)
        print(final_response)
        print("="*50)
        
    except Exception as e:
        print(f"[!] Execution Error: {str(e)}")

if __name__ == "__main__":
    # Menjalankan async function
    asyncio.run(main())