import asyncio
from core.orchestrator import PemaliOrchestrator

async def main():
    # 1. Tentukan session_id unik untuk audit ini
    session_id = "audit-ubud-001"
    
    # 2. Inisialisasi Orchestrator (The Brain)
    # Pastikan model name sesuai dengan yang tersedia di OpenRouter
    agent = PemaliOrchestrator(session_id=session_id)
    
    # 3. Berikan instruksi awal
    # Prompt ini didesain untuk memicu ReAct loop (manggil satellite tool dulu baru report)
    prompt = (
        "Lakukan audit di Ubud sekarang, dan jadwalkan pemeriksaan ulang otomatis 1 menit dari sekarang untuk memastikan data tidak berubah."
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