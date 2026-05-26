"""
OSINT Web Search — DuckDuckGo-based web search for real-time public data.
Sub-Agent dapat memanggil modul ini untuk mencari berita dan data publik.
No API key required.
"""
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from ddgs import DDGS

from backend.core.base_module import (
    PemaliModuleV2, ModuleOutput, THKAlignment, THKPresets
)


class OSINTInput(BaseModel):
    """Schema input untuk pencarian OSINT berbasis web."""
    query: str = Field(
        ...,
        description="Query pencarian spesifik. Contoh: 'kebakaran hutan kintamani hari ini'.",
    )
    search_depth: str = Field(
        default="advanced",
        description="Kedalaman pencarian: 'basic' atau 'advanced'.",
    )
    max_results: int = Field(
        default=5,
        description="Jumlah maksimal hasil pencarian yang dikembalikan.",
    )


class OSINTWebSearch(PemaliModuleV2):
    """Modul OSINT berbasis DuckDuckGo. Menyediakan pencarian web real-time tanpa API key."""

    @property
    def name(self) -> str:
        return "osint_web_search"

    @property
    def description(self) -> str:
        return "Mencari berita, data publik, dan informasi terkini dari seluruh web (OSINT) via DuckDuckGo. Unlimited queries, no API key."

    @property
    def input_schema(self):
        return OSINTInput

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def tags(self) -> List[str]:
        return ["osint", "search", "news", "intelligence"]

    @property
    def output_example(self) -> Dict[str, Any]:
        return {
            "status": 200,
            "data": {
                "query": "kebakaran hutan bali",
                "total_results": 3,
                "results": []
            },
            "agent_hint": "RINGKASAN OSINT: 3 hasil ditemukan untuk 'kebakaran hutan bali'.",
            "thk_alignment": {
                "parahyangan": "...",
                "pawongan": "...",
                "palemahan": "..."
            }
        }

    async def execute(self, params: OSINTInput, context: Dict[str, Any]) -> ModuleOutput:
        max_results = min(params.max_results, 10)

        try:
            def search():
                with DDGS() as ddgs:
                    return list(ddgs.text(params.query, max_results=max_results))
            results = await asyncio.to_thread(search)

            formatted_results = [
                {"title": r.get("title", ""), "url": r.get("href", ""), "content": r.get("body", "")[:500]}
                for r in results
            ]

            hint = f"RINGKASAN OSINT: {len(formatted_results)} hasil ditemukan untuk '{params.query[:60]}'."
            if formatted_results:
                hint += f" Sumber teratas: {formatted_results[0]['title'][:60]}"

            return ModuleOutput(
                status=200,
                data={
                    "query": params.query,
                    "total_results": len(formatted_results),
                    "results": formatted_results,
                    "backend": "duckduckgo",
                },
                agent_hint=hint,
                thk_alignment=THKPresets.data_processing("DuckDuckGo OSINT Engine")
            )

        except Exception as e:
            return ModuleOutput(
                status=500,
                error_msg=f"DuckDuckGo search error: {str(e)}",
                agent_hint="Gagal melakukan pencarian web via DuckDuckGo."
            )


module = OSINTWebSearch()
