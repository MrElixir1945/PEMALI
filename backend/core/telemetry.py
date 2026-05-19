import asyncio
import json
import logging
import os
from typing import AsyncGenerator
from backend.core.models import TelemetryEvent, NodeState

logger = logging.getLogger(__name__)

class TelemetryManager:
    def __init__(self):
        self.queues: list[asyncio.Queue] = []
        self.remote_url = os.getenv("TELEMETRY_REMOTE_URL", "")

    async def subscribe(self) -> AsyncGenerator[str, None]:
        queue = asyncio.Queue()
        self.queues.append(queue)
        logging.info(f"[Telemetry] New subscriber. Total queues: {len(self.queues)}")
        try:
            while True:
                data = await queue.get()
                logging.info(f"[Telemetry] Emitting event: {data.get('node_id')} - {data.get('state')}")
                yield f"data: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            logging.info("[Telemetry] Subscriber cancelled")
            pass
        except Exception as e:
            logging.error(f"[Telemetry] Subscribe error: {e}")
        finally:
            if queue in self.queues:
                self.queues.remove(queue)
                logging.info(f"[Telemetry] Subscriber removed. Total queues: {len(self.queues)}")

    async def _post_remote(self, data: dict):
        """Worker process: POST event ke FastAPI agar diteruskan ke SSE subscribers."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(self.remote_url, json=data)
                if res.status_code == 200:
                    logger.debug(f"[Telemetry] Remote publish OK: {data.get('node_id')}")
                else:
                    logger.warning(f"[Telemetry] Remote publish failed: HTTP {res.status_code}")
        except Exception as e:
            logger.warning(f"[Telemetry] Remote publish error: {e}")

    async def emit(self, event: TelemetryEvent):
        data = event.model_dump(mode='json')
        for queue in self.queues:
            try:
                await queue.put(data)
            except Exception as e:
                logger.error(f"[Telemetry] Emit error: {e}")
        if not self.queues:
            if self.remote_url:
                await self._post_remote(data)
            else:
                logger.warning(f"[Telemetry] Event emitted but no subscribers: {data.get('node_id')} - {data.get('state')}")
        await asyncio.sleep(0)

    async def emit_dict(self, data: dict):
        """Emit raw dict event to all subscribers (for high-frequency token events)."""
        for queue in self.queues:
            try:
                await queue.put(data)
            except Exception as e:
                logger.error(f"[Telemetry] emit_dict error: {e}")
        await asyncio.sleep(0)

telemetry = TelemetryManager()