import os
import logging
import asyncio
import time
from openai import AsyncOpenAI

OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash:free")

logger = logging.getLogger("PEMALI.LLMClient")

_llm_client: AsyncOpenAI | None = None
_last_call = time.monotonic()
MIN_INTERVAL = 1.0


async def rate_limit_wait():
    """Rate limiter — min 1s antar LLM call. Tanpa global lock biar concurrent agent gak saling blok."""
    global _last_call
    elapsed = time.monotonic() - _last_call
    if elapsed < MIN_INTERVAL:
        wait = MIN_INTERVAL - elapsed
        logger.info(f"[RateLimit] Cooling down {wait:.1f}s")
        await asyncio.sleep(wait)
    _last_call = time.monotonic()


def get_llm_client() -> AsyncOpenAI:
    global _llm_client
    if _llm_client is None:
        _llm_client = AsyncOpenAI(
            base_url="https://opencode.ai/zen/go/v1",
            api_key=OPENROUTER_KEY,
        )
        logger.info(f"LLM client initialized: {OPENROUTER_MODEL}")
    return _llm_client
