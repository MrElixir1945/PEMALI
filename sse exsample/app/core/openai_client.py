"""
Singleton AsyncOpenAI client
=============================
Dibuat sekali saat aplikasi pertama kali pakai,
di-reuse untuk semua request. Hemat TCP handshake + SSL overhead.
"""
from openai import AsyncOpenAI

_client: AsyncOpenAI | None = None


def get_async_client(api_key: str, base_url: str) -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return _client