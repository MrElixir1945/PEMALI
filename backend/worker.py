import logging
import asyncio
import datetime
import time
import sys
import os

# Ensure project root is in Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cross-process: worker emits to FastAPI SSE via HTTP POST (fallback to backend env config)
_backend_url = os.getenv("BACKEND_URL") or os.getenv("NEXT_PUBLIC_BACKEND_URL") or "http://localhost:8080"
_remote_url = f"{_backend_url.rstrip('/')}/api/telemetry/publish"
os.environ.setdefault("TELEMETRY_REMOTE_URL", _remote_url)

from sqlalchemy.orm import Session
from backend.core.database import SessionLocal, init_db, AutonomousTask
from backend.core.orchestrator import PemaliOrchestrator
from backend.core.autonomous_mind import AutonomousMind
from backend.core.telemetry import telemetry
from backend.core.models import TelemetryEvent, NodeState

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("WorkerDaemon")

# Batasi maksimal 5 tugas otonom berjalan bersamaan agar tidak overload
WORKER_CONCURRENCY = 5
worker_semaphore = asyncio.Semaphore(WORKER_CONCURRENCY)


async def execute_autonomous_mind(task_id: int, priority: int):
    """Agent Otak — full strategic loop: decide cases + spawn runners + self-schedule."""
    async with worker_semaphore:
        trace_id = f"auto-mind-{task_id}-{int(time.time())}"

        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="worker_daemon", node_type="System",
            state=NodeState.THINKING, narrative=f"Agent Otak diaktifkan untuk siklus otonom #{task_id}",
            metadata={"task_id": task_id, "priority": priority}
        ))

        mind = AutonomousMind(trace_id)
        try:
            overview = await mind.wake(task_id, priority)

            with SessionLocal() as db:
                t = db.query(AutonomousTask).filter(AutonomousTask.id == task_id).first()
                if t:
                    t.status = "completed"
                    db.commit()

            await telemetry.emit(TelemetryEvent(
                trace_id=trace_id, node_id="worker_daemon", node_type="System",
                state=NodeState.DONE,
                narrative=f"Siklus otonom selesai: {overview.get('total_cases', 0)} kasus diaudit. "
                         f"{overview.get('success', 0)} sukses, {overview.get('failed', 0)} gagal."
            ))
        except Exception as e:
            logger.error(f"AutonomousMind task {task_id} failed: {e}")
            with SessionLocal() as db:
                t = db.query(AutonomousTask).filter(AutonomousTask.id == task_id).first()
                if t:
                    t.status = "failed"
                    t.retries = (t.retries or 0) + 1
                    t.last_error = str(e)[:500]
                    db.commit()

            await telemetry.emit(TelemetryEvent(
                trace_id=trace_id, node_id="worker_daemon", node_type="System",
                state=NodeState.ERROR, narrative=f"Siklus otonom gagal: {str(e)[:200]}"
            ))


async def execute_autonomous_task(task_id: int, intent_description: str):
    """Direct execution — jalankan orchestrator langsung (one-shot autonomous task)."""
    async with worker_semaphore:
        trace_id = f"auto-{task_id}-{int(time.time())}"

        await telemetry.emit(TelemetryEvent(
            trace_id=trace_id, node_id="worker_daemon", node_type="System",
            state=NodeState.THINKING, narrative=f"Mengeksekusi rencana otonom: {intent_description[:100]}"
        ))

        agent = PemaliOrchestrator(session_id=trace_id)
        # Set autonomous mode for direct tasks
        agent.set_autonomous_mode(source="autonomous", priority=5, case_title=intent_description[:80])
        try:
            await agent.run(intent_description)

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
                    task.retries = (task.retries or 0) + 1
                    task.last_error = str(e)[:500]
                    db.commit()

            await telemetry.emit(TelemetryEvent(
                trace_id=trace_id, node_id="worker_daemon", node_type="System",
                state=NodeState.ERROR, narrative=f"Kegagalan eksekusi otonom: {str(e)[:200]}"
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
    STUCK_TIMEOUT_MINUTES = 30

    while True:
        try:
            with SessionLocal() as db:
                now = datetime.datetime.now(datetime.timezone.utc)

                # Watchdog: recover stuck tasks (created > STUCK_TIMEOUT_MINUTES lalu masih running)
                stuck_deadline = now - datetime.timedelta(minutes=STUCK_TIMEOUT_MINUTES)
                stuck_tasks = db.query(AutonomousTask).filter(
                    AutonomousTask.status == "running",
                    AutonomousTask.created_at <= stuck_deadline
                ).all()
                for st in stuck_tasks:
                    logger.warning(f"Watchdog: recovering stuck task {st.id} (running > {STUCK_TIMEOUT_MINUTES}m)")
                    st.status = "failed"
                    st.last_error = f"Watchdog: task stuck in 'running' for >{STUCK_TIMEOUT_MINUTES} minutes"
                    st.retries = (st.retries or 0) + 1
                db.commit()

                # SPRINT-5: Ambil task sorted by priority DESC (urgensi dulu)
                tasks = db.query(AutonomousTask).filter(
                    AutonomousTask.status == "pending",
                    AutonomousTask.execute_at <= now
                ).order_by(
                    AutonomousTask.priority.desc(),
                    AutonomousTask.execute_at.asc()
                ).all()

                for task in tasks:
                    # Capture task attributes to avoid SQLAlchemy DetachedInstanceError in async task
                    task_id = task.id
                    task_priority = task.priority
                    task_type = task.task_type
                    task_intent = task.intent_description or ""

                    logger.info(f"Triggering Task ID: {task_id} type={task_type} priority={task_priority} — {task_intent[:80] if task_intent else '-'}")
                    task.status = "running"
                    db.commit()

                    # SPRINT-5: Routing berdasarkan task_type
                    if task_type == "autonomous":
                        asyncio.create_task(execute_autonomous_mind(task_id, task_priority))
                    else:
                        asyncio.create_task(execute_autonomous_task(task_id, task_intent))

        except Exception as e:
            logger.error(f"Runtime Loop Error: {e}")

        await asyncio.sleep(15)


if __name__ == "__main__":
    try:
        asyncio.run(process_autonomous_queue())
    except KeyboardInterrupt:
        logger.info("Stopping heartbeat engine...")
