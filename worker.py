import asyncio
import datetime
import time
import sys
from sqlalchemy.orm import Session
from core.database import SessionLocal, AutonomousTask, init_db

async def check_and_execute_tasks():
    print("[Worker] Initializing database tables...")
    
    # Retry logic for database connection
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
    
    print("[Worker] Heartbeat started. Monitoring autonomous_tasks...")
    
    while True:
        db = None
        try:
            db = SessionLocal()
            if not db:
                print("[Worker] Failed to create database session. Retrying in 10s...")
                await asyncio.sleep(10)
                continue

            now = datetime.datetime.now(datetime.timezone.utc)
            
            # 1. Cari tugas yang statusnya 'pending' dan sudah masuk waktunya (execute_at <= now)
            pending_task = db.query(AutonomousTask).filter(
                AutonomousTask.status == "pending",
                AutonomousTask.execute_at <= now
            ).with_for_update(skip_locked=True).first()

            if pending_task:
                print(f"[Worker] Triggering Task ID: {pending_task.id} - Reason: {pending_task.intent_description}")
                
                # 2. Re-activate Orchestrator
                from core.orchestrator import PemaliOrchestrator
                session_id = f"auto-{pending_task.id}"
                agent = PemaliOrchestrator(session_id=session_id)
                
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
        except Exception as e:
            print(f"[Worker] Runtime Error: {e}")
        finally:
            if db:
                db.close()
        
        # Cek setiap 30 detik
        await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(check_and_execute_tasks())
    except KeyboardInterrupt:
        print("[Worker] Stopping...")