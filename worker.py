import asyncio
import datetime
import time
from sqlalchemy.orm import Session
from core.database import SessionLocal, AutonomousTask, init_db
from core.orchestrator import PemaliOrchestrator

async def check_and_execute_tasks():
    print("[Worker] Initializing database tables...")
    init_db()
    
    print("[Worker] Heartbeat started. Monitoring autonomous_tasks...")
    
    while True:
        db: Session = SessionLocal()
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # 1. Cari tugas yang statusnya 'pending' dan sudah masuk waktunya (execute_at <= now)
        pending_task = db.query(AutonomousTask).filter(
            AutonomousTask.status == "pending",
            AutonomousTask.execute_at <= now
        ).first()

        if pending_task:
            print(f"[Worker] Triggering Task ID: {pending_task.id} - Reason: {pending_task.intent_description}")
            
            # 2. Re-activate Orchestrator
            # Gunakan session_id yang sama agar memori tetap nyambung
            session_id = f"auto-{pending_task.id}"
            agent = PemaliOrchestrator(session_id=session_id)
            
            # Masukkan context snapshot sebagai prompt awal
            prompt = f"Executing scheduled task. Context: {pending_task.intent_description}"
            
            try:
                # Update status jadi running agar tidak dieksekusi worker lain
                pending_task.status = "running"
                db.commit()
                
                await agent.run(prompt)
                
                # 3. Mark as completed
                pending_task.status = "completed"
                print(f"[Worker] Task {pending_task.id} completed successfully.")
            except Exception as e:
                pending_task.status = "failed"
                print(f"[Worker] Task {pending_task.id} failed: {str(e)}")
            
            db.commit()
        
        db.close()
        # Cek setiap 30 detik agar tidak membebani CPU/DB
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(check_and_execute_tasks())