import asyncio
import json
import sys
from core.orchestrator import PemaliOrchestrator
from core.telemetry import telemetry
from core.memory import query_semantic

async def telemetry_logger():
    """Mendengarkan stream telemetry dan mencetaknya ke console dengan format rapi."""
    print("\n[STREAM] Listening to Agent Cognition...")
    async for event_str in telemetry.subscribe():
        # Parse SSE format "data: {...}\n\n"
        try:
            raw_json = event_str.replace("data: ", "").strip()
            if not raw_json: continue
            
            event = json.loads(raw_json)
            node = event.get("node_id", "???")
            state = event.get("state", "UNKNOWN")
            narrative = event.get("narrative", "")
            
            # Warna-warni sederhana untuk console
            color = "\033[94m" # Blue
            if state == "EXECUTING": color = "\033[93m" # Yellow
            if state == "DONE": color = "\033[92m" # Green
            if state == "ERROR": color = "\033[91m" # Red
            
            print(f"{color}[{state}] {node}: {narrative}\033[0m")
        except Exception as e:
            pass

async def run_test():
    session_id = f"test-v2-{int(asyncio.get_event_loop().time())}"
    agent = PemaliOrchestrator(session_id=session_id)
    
    # Prompt yang akan memicu Mock Data (V2) dan Scheduler (V2)
    prompt = (
        "Coba simulasikan data ekologi di Ubud menggunakan mock generator. "
        "Setelah itu, jadwalkan pemeriksaan ulang otomatis 1 menit dari sekarang "
        "dengan pesan 'Lakukan validasi data simulasi Ubud'."
    )
    
    print(f"[*] Starting PEMALI V2 Test Session: {session_id}")
    print(f"[*] Prompt: {prompt}\n")

    # Jalankan telemetry logger di background
    logger_task = asyncio.create_task(telemetry_logger())
    
    try:
        # Jalankan Orchestrator
        final_response = await agent.run(prompt)
        
        print("\n" + "="*60)
        print("FINAL AGENT REPORT (Synthesized):")
        print("="*60)
        print(final_response)
        print("="*60)

        # Verifikasi RAG / Semantic Memory
        print("\n[*] Verifying Semantic Memory (RAG)...")
        memories = query_semantic("simulasi ekologi Ubud")
        if memories:
            print(f"[✓] Found {len(memories)} relevant memories in ChromaDB.")
            for i, m in enumerate(memories):
                print(f"    {i+1}. {m['content'][:100]}...")
        else:
            print("[✗] No semantic memory found. Check ChromaDB/Memory Layer.")

    except Exception as e:
        print(f"\n[!] Fatal Error during test: {str(e)}")
    finally:
        # Beri waktu sebentar agar log terakhir muncul
        await asyncio.sleep(2)
        logger_task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        print("\n[!] Test interrupted.")
        sys.exit(0)