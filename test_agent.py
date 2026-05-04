import asyncio
from core.orchestrator import PemaliOrchestrator

async def main():
    agent = PemaliOrchestrator(session_id="test_mem_01")
    print("Memulai audit ekologi Bedugul...")
    hasil = await agent.run("Lakukan audit ekologi di kawasan Bedugul dan cek proyeksi krisis air.")
    print("\n--- KEPUTUSAN AKHIR CRITIC ---")
    print(hasil)

if __name__ == "__main__":
    asyncio.run(main())