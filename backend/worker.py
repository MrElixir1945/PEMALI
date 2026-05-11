import logging
import asyncio
import datetime
import time
import sys
from sqlalchemy.orm import Session
from backend.core.database import SessionLocal, init_db, AutonomousTask
from backend.core.orchestrator import PemaliOrchestrator
from backend.core.telemetry import telemetry
from backend.core.models import TelemetryEvent, NodeState

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("WorkerDaemon")

# Batasi maksimal 5 tugas otonom berjalan bersamaan agar tidak overload
WORKER_CONCURRENCY = 5
worker_semaphore = asyncio.Semaphore(WORKER_CONCURRENCY)

async def execute_autonomous_task(task_id: int, intent_description: str):
    """Berjalan terisolasi di background dengan kontrol semaphore."""
    async with worker_semaphore:
        trace_id = f"auto-{task_id}-{int(time.time())}"
        
        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="worker_daemon", node_type="System",
            state=NodeState.THINKING, narrative=f"Mengeksekusi rencana otonom: {intent_description}"
        ))
        
        agent = PemaliOrchestrator(session_id=trace_id)
        try:
            # 1. Jalankan logika AI (Ini memakan waktu lama)
            await agent.run(intent_description)
            
            # 2. Update status ke completed (Gunakan session baru agar tidak stale)
            with SessionLocal() as db:
                task = db.query(AutonomousTask).filter(AutonomousTask.id == task_id).first()
                if task:
                    task.status = "completed"
                    db.commit()
                
            await telemetry.emit(TelemetryEvent(
                trace_id=trace_id, node_id="worker_daemon", node_type="System",
                state=NodeState.DONE, narrative="Tugas otonom berhasil diselesaikan."
            ))
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            with SessionLocal() as db:
                task = db.query(AutonomousTask).filter(AutonomousTask.id == task_id).first()
                if task:
                    task.status = "failed"
                    db.commit()
                
            await telemetry.emit(TelemetryEvent(
                trace_id=trace_id, node_id="worker_daemon", node_type="System",
                state=NodeState.ERROR, narrative=f"Kegagalan eksekusi otonom: {str(e)}"
            ))

async def process_autonomous_queue():
    """Loop utama, memproses semua task yang jatuh tempo sekaligus."""
    logger.info("Initializing database tables...")
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            init_db()
            logger.info("Database initialized successfully.")
            break
        except Exception as e:
            logger.warning(f"Database connection failed (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
            else:
                logger.error("Max retries reached. Exiting.")
                sys.exit(1)
    
    logger.info("Tick Engine started. Monitoring autonomous_tasks table...")
    
    while True:
        try:
            with SessionLocal() as db:
                now = datetime.datetime.now(datetime.timezone.utc)
                
                # AMBIL SEMUA task yang pending dan sudah masuk waktunya
                tasks = db.query(AutonomousTask).filter(
                    AutonomousTask.status == "pending",
                    AutonomousTask.execute_at <= now
                ).all()
                
                for task in tasks:
                    logger.info(f"Triggering Task ID: {task.id} - {task.intent_description}")
                    task.status = "running"
                    db.commit()
                    
                    # Jalankan di background
                    asyncio.create_task(execute_autonomous_task(task.id, task.intent_description))
                
        except Exception as e:
            logger.error(f"Runtime Loop Error: {e}")
            
        await asyncio.sleep(15)

if __name__ == "__main__":
    try:
        asyncio.run(process_autonomous_queue())
    except KeyboardInterrupt:
        logger.info("Stopping heartbeat engine...")