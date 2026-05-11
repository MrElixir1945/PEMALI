import asyncio
import json
from typing import AsyncGenerator
from backend.core.models import TelemetryEvent, NodeState

class TelemetryManager:
    def __init__(self):
        self.queues: list[asyncio.Queue] = []

    async def subscribe(self) -> AsyncGenerator[str, None]:
        queue = asyncio.Queue()
        self.queues.append(queue)
        try:
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            # Triggered saat client (Next.js) force disconnect
            pass 
        finally:
            if queue in self.queues:
                self.queues.remove(queue)

    async def emit(self, event: TelemetryEvent):
        """Kirim event ke semua listener (seperti Dashboard)."""
        data = event.model_dump()
        for queue in self.queues:
            await queue.put(data)

telemetry = TelemetryManager()