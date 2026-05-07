import asyncio
import datetime
import time
import sys
from sqlalchemy.orm import Session
from core.database import SessionLocal, AutonomousTask, init_db
from core.orchestrator import PemaliOrchestrator
from core.telemetry import telemetry
from core.models import TelemetryEvent, NodeState

async def process_autonomous_queue():
    """
    Loop utama untuk memantau tugas otonom yang terjadwal.
    Mengintegrasikan retry logic DB dan telemetry stream.
    """
    print("[Worker] Initializing database tables...")
    
    # 1. Retry logic untuk koneksi database awal
    max_retries = 5
    retry_count = 0
    while retry_count < max_retries:
        try:
            init_db()
            print("[Worker] Database initialized successfully.")
            break
        except Exception as e:
            retry_count += 1
            print(f"[Worker] Database connection failed (Attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                print("[Worker] Retrying in 5 seconds...")
                await asyncio.sleep(5)
            else:
                print("[Worker] Max retries reached. Exiting.")
                sys.exit(1)
    
    print("[Worker] Tick Engine started. Monitoring autonomous_tasks table...")
    
    while True:
        db = None
        try:
            db = SessionLocal()
            if not db:
                await asyncio.sleep(10)
                continue

            # Gunakan UTC untuk konsistensi jadwal
            now = datetime.datetime.now(datetime.timezone.utc)
            
            # 2. Cari tugas yang statusnya 'pending' dan sudah masuk waktunya
            task = db.query(AutonomousTask).filter(
                AutonomousTask.status == "pending",
                AutonomousTask.execute_at <= now
            ).order_by(AutonomousTask.execute_at.asc()).first()
            
            if task:
                print(f"[Worker] Triggering Task ID: {task.id} - {task.intent_description}")
                
                # Update status ke running agar tidak di-pick worker lain
                task.status = "running"
                db.commit()
                
                # 3. Emit telemetry: Memberitahu UI bahwa proses otonom dimulai
                trace_id = f"auto-{task.id}-{int(time.time())}"
                await telemetry.emit(TelemetryEvent(
                    trace_id=trace_id,
                    node_id="worker_daemon",
                    node_type="System",
                    state=NodeState.THINKING,
                    narrative=f"Mengeksekusi rencana otonom: {task.intent_description}"
                ))
                
                # 4. Jalankan Orchestrator (The Brain)
                agent = PemaliOrchestrator(session_id=trace_id)
                
                try:
                    await agent.run(task.intent_description)
                    task.status = "completed"
                    
                    await telemetry.emit(TelemetryEvent(
                        trace_id=trace_id,
                        node_id="worker_daemon",
                        node_type="System",
                        state=NodeState.DONE,
                        narrative="Tugas otonom berhasil diselesaikan."
                    ))
                except Exception as e:
                    task.status = "failed"
                    print(f"[Worker] Task execution failed: {e}")
                    
                    await telemetry.emit(TelemetryEvent(
                        trace_id=trace_id,
                        node_id="worker_daemon",
                        node_type="System",
                        state=NodeState.ERROR,
                        narrative=f"Kegagalan eksekusi otonom: {str(e)}"
                    ))
                
                db.commit()
            
        except Exception as e:
            print(f"[Worker] Runtime Loop Error: {e}")
        finally:
            if db:
                db.close()
            
        # Polling interval: Cek setiap 15 detik
        await asyncio.sleep(15)

if __name__ == "__main__":
    try:
        asyncio.run(process_autonomous_queue())
    except KeyboardInterrupt:
        print("[Worker] Stopping heartbeat engine...")