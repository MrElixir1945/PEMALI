"""
OSINT Trend Scanner — Batch DuckDuckGo queries with sentiment analysis and trend detection.
Sub-Agent dapat memanggil modul ini untuk scan tren isu lingkungan di Bali.
No API key required — unlimited queries via DuckDuckGo.
"""
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from ddgs import DDGS

from backend.core.base_module import (
    PemaliModuleV2,
    ModuleOutput,
    THKAlignment,
    THKPresets,
)

POSITIVE_WORDS = {"baik", "membaik", "menurun", "tertangani", "pulih", "normal", "aman", "sehat", "stabil"}
NEGATIVE_WORDS = {"kritis", "darurat", "meningkat", "meluas", "parah", "berbahaya", "mencemaskan", "gawat", "rusak", "mengkhawatirkan", "bencana"}
DDG_DELAY = 0.8


class OSINTTrendInput(BaseModel):
    """Input untuk batch OSINT trend scanning via DuckDuckGo."""
    keywords: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Keywords pencarian (1-5 keywords). Contoh: ['kebakaran hutan Bali', 'banjir Bali']",
    )
    max_results_per_keyword: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Jumlah hasil per keyword (default 3, total max 25 results)",
    )
    history_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Lookback days untuk trend analysis",
    )
    region: str = Field(
        default="Bali",
        description="Region context untuk analysis",
    )


class OSINTTrendScanner(PemaliModuleV2):
    """Batch OSINT trend scanner — DuckDuckGo backend, unlimited free queries."""

    @property
    def name(self) -> str:
        return "osint_trend_scanner"

    @property
    def description(self) -> str:
        return "Batch OSINT trend scanner — multiple keywords, DuckDuckGo search, sentiment analysis, and trend scoring. No API key needed."

    @property
    def input_schema(self):
        return OSINTTrendInput

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def tags(self) -> List[str]:
        return ["osint", "trend", "sentiment", "batch"]

    @property
    def output_example(self) -> Dict[str, Any]:
        return {
            "status": 200,
            "data": {
                "timestamp": "",
                "keywords_used": ["kebakaran hutan Bali", "banjir Bali"],
                "total_results": 6,
                "trends": [],
                "analysis": {"hot_topics": [], "overall_sentiment": "neutral", "urgency": "low"},
            },
            "agent_hint": "TREND SCAN: 2 topik dipindai. Status: normal.",
            "thk_alignment": {"parahyangan": "...", "pawongan": "...", "palemahan": "..."},
        }

    async def execute(self, params: OSINTTrendInput, context: Dict[str, Any]) -> ModuleOutput:
        keywords = params.keywords[:5]
        batch_size = min(params.max_results_per_keyword, 5)

        async def search_one(query: str) -> dict:
            try:
                await asyncio.sleep(DDG_DELAY)
                def search():
                    with DDGS() as ddgs:
                        return list(ddgs.text(query, max_results=batch_size))
                results = await asyncio.to_thread(search)
                return {"query": query, "status": "ok", "data": results}
            except Exception as e:
                return {"query": query, "status": "error", "error": str(e)}

        raw_results = await asyncio.gather(*[search_one(q) for q in keywords])

        trends = []
        errors = []
        total_results = 0

        for r in raw_results:
            if r["status"] != "ok":
                errors.append({"query": r["query"], "error": r.get("error", "unknown")})
                continue

            hits = r["data"]
            total_results += len(hits)

            total_content = " ".join(h.get("body", "") for h in hits).lower() if hits else ""
            pos_count = sum(1 for w in POSITIVE_WORDS if w in total_content)
            neg_count = sum(1 for w in NEGATIVE_WORDS if w in total_content)

            if pos_count > neg_count:
                sentiment = "positif"
            elif neg_count > pos_count:
                sentiment = "negatif"
            else:
                sentiment = "netral"

            trend_score = len(hits) * 0.6
            if hits:
                trend_score += 0.4

            trends.append({
                "query": r["query"],
                "count": len(hits),
                "sentiment": sentiment,
                "trend_score": round(trend_score, 2),
                "results_sample": [
                    {"title": h.get("title", ""), "url": h.get("href", ""), "content": h.get("body", "")[:300]}
                    for h in hits[:max(batch_size, 3)]
                ],
            })

        pos_count = sum(1 for t in trends if t["sentiment"] == "positif")
        neg_count = sum(1 for t in trends if t["sentiment"] == "negatif")
        top_trends = sorted(trends, key=lambda x: x["trend_score"], reverse=True)[:3]

        if neg_count > pos_count:
            overall_sentiment = "negatif"
            urgency = "high" if neg_count >= len(trends) * 0.6 else "medium"
        elif pos_count > neg_count:
            overall_sentiment = "positif"
            urgency = "low"
        else:
            overall_sentiment = "netral"
            urgency = "low"

        hint_parts = [f"TREND SCAN: {len(trends)}/{len(keywords)} topik dipindai."]
        if neg_count > 0:
            hint_parts.append(f"{neg_count} topik tren negatif.")
        if top_trends:
            hint_parts.append(f"Top: {', '.join(t['query'][:25] for t in top_trends)}.")
        if errors:
            hint_parts.append(f"{len(errors)} query gagal.")

        return ModuleOutput(
            status=200,
            data={
                "timestamp": "",
                "keywords_used": keywords,
                "total_results": total_results,
                "trends": trends,
                "analysis": {
                    "hot_topics": [{"query": t["query"], "score": t["trend_score"]} for t in top_trends],
                    "overall_sentiment": overall_sentiment,
                    "urgency": urgency,
                    "positive_count": pos_count,
                    "negative_count": neg_count,
                },
                "errors": errors if errors else None,
                "backend": "duckduckgo",
                "rate_limit_delay_s": DDG_DELAY,
            },
            agent_hint=" ".join(hint_parts),
            thk_alignment=THKPresets.data_processing("OSINT Trend Scanner (DuckDuckGo)"),
        )


module = OSINTTrendScanner()
