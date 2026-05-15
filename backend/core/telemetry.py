import asyncio
import json
import logging
from typing import AsyncGenerator
from backend.core.models import TelemetryEvent, NodeState

logger = logging.getLogger(__name__)

class TelemetryManager:
    def __init__(self):
        self.queues: list[asyncio.Queue] = []

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

    async def emit(self, event: TelemetryEvent):
        data = event.model_dump(mode='json')
        for queue in self.queues:
            try:
                await queue.put(data)
            except Exception as e:
                logger.error(f"[Telemetry] Emit error: {e}")
        if not self.queues:
            logger.warning(f"[Telemetry] Event emitted but no subscribers: {data.get('node_id')} - {data.get('state')}")
        await asyncio.sleep(0)

telemetry = TelemetryManager()