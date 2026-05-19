"""
OSINT Instagram Monitor — scrape post & komentar Instagram, analisis emosi publik.
Module zero-narrative: scraper + dedicated LLM call untuk emotion analysis.
Flow: DDGS search → shortcode extract → Instaloader scrape → LLM analysis → UTI V2.
"""
import asyncio
import json
import re
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from ddgs import DDGS

from backend.core.base_module import (
    PemaliModuleV2, ModuleOutput, THKAlignment, THKPresets
)
from backend.core.llm_client import get_llm_client, OPENROUTER_MODEL

DDG_DELAY = 0.8
MAX_RETRY_SCRAPE = 2


class InstagramMonitorInput(BaseModel):
    issue: str = Field(
        ..., description="Isu yang mau dipantau. Contoh: 'sampah plastik pantai kuta'",
        min_length=3, max_length=200
    )
    date_from: Optional[str] = Field(
        None, description="Tanggal awal filter (YYYY-MM-DD). Contoh: '2026-05-01'"
    )
    date_to: Optional[str] = Field(
        None, description="Tanggal akhir filter (YYYY-MM-DD). Contoh: '2026-05-15'"
    )
    days_back: Optional[int] = Field(
        None, ge=1, le=365,
        description="Alternatif filter: ambil post N hari terakhir. Contoh: 7"
    )
    max_posts: int = Field(
        default=10, ge=1, le=30,
        description="Maksimal post yang di-scrape"
    )
    include_comments: bool = Field(
        default=True,
        description="Scrape top 5 komentar (by likes) per post"
    )
    location_hint: Optional[str] = Field(
        None, description="Hint lokasi. Contoh: 'Kuta, Bali'"
    )
    instagram_login: Optional[str] = Field(
        None, description="Username Instagram (opsional, akses lebih banyak)"
    )
    instagram_password: Optional[str] = Field(
        None, description="Password Instagram (opsional)"
    )


class OSINTInstagramMonitor(PemaliModuleV2):
    """OSINT Instagram Monitor — scrape + emotion analysis."""

    @property
    def name(self) -> str:
        return "osint_instagram_monitor"

    @property
    def description(self) -> str:
        return (
            "Mencari dan menganalisis reaksi masyarakat di Instagram terhadap suatu isu. "
            "Scrape post, caption, likes, dan komentar, lalu analisis emosi dominan "
            "(marah/sedih/khawatir/dukung/kritis/apati/ajakan). "
            "Gunakan untuk memonitor opini publik tentang isu lingkungan atau sosial."

        )

    @property
    def input_schema(self):
        return InstagramMonitorInput

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def tags(self) -> List[str]:
        return ["osint", "instagram", "sentiment", "social-media", "monitoring"]

    @property
    def output_example(self) -> Dict[str, Any]:
        return {
            "status": 200,
            "data": {
                "issue": "sampah plastik pantai kuta",
                "period": {"date_from": "2026-05-12", "date_to": "2026-05-19"},
                "scrape_summary": {"total_shortcodes_found": 12, "total_posts_scraped": 8},
                "posts": [],
                "llm_analysis": {
                    "emotions": {"marah": 3, "sedih": 5, "khawatir": 2, "dukung": 0,
                                "kritis": 4, "apati": 1, "ajakan": 2},
                    "dominant_tone": "sedih",
                    "evidence": [],
                    "trend_summary": ""
                }
            },
            "agent_hint": "INSTAGRAM MONITOR: 8 post tentang 'sampah plastik pantai kuta'. Emosi dominan: sedih.",
            "thk_alignment": {"parahyangan": "...", "pawongan": "...", "palemahan": "..."}
        }

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    def _resolve_date_range(self, params: InstagramMonitorInput) -> tuple:
        now = datetime.now(timezone.utc)
        if params.date_from and params.date_to:
            return self._parse_date(params.date_from), self._parse_date(params.date_to)
        days = params.days_back or 7
        return now - timedelta(days=days), now

    @staticmethod
    def _search_instagram_urls(issue: str, location_hint: Optional[str]) -> List[Dict]:
        queries = [f"site:instagram.com {issue}"]
        if location_hint:
            queries.append(f"site:instagram.com {issue} {location_hint}")
        queries.append(f"{issue} instagram")

        seen_urls = set()
        results = []

        for query in queries:
            try:
                with DDGS() as ddgs:
                    hits = list(ddgs.text(query, max_results=10))
                for h in hits:
                    url = h.get("href", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        results.append({
                            "title": h.get("title", ""),
                            "url": url,
                            "content": h.get("body", "")[:300]
                        })
            except Exception:
                continue

        return results

    @staticmethod
    def _extract_shortcodes(results: List[Dict]) -> List[str]:
        pattern = re.compile(
            r'(?<![a-zA-Z0-9])instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)'
        )
        shortcodes = []
        seen = set()
        for r in results:
            url = r.get("url", "")
            match = pattern.search(url)
            if match:
                code = match.group(1)
                if code not in seen:
                    seen.add(code)
                    shortcodes.append(code)
        return shortcodes

    async def _scrape_post(self, shortcode: str, date_from: datetime,
                           date_to: datetime, include_comments: bool,
                           instaloader_kwargs: Dict) -> Optional[Dict]:
        def _sync_scrape():
            from instaloader import Instaloader, Post
            loader = Instaloader(**instaloader_kwargs)
            post = Post.from_shortcode(loader.context, shortcode)
            return post

        try:
            post = await asyncio.to_thread(_sync_scrape)
        except Exception:
            return None

        post_date = post.date_local.replace(tzinfo=timezone.utc) if post.date_local.tzinfo \
            else post.date_local.replace(tzinfo=timezone.utc)

        if post_date < date_from or post_date > date_to:
            return None

        comments_sample = []
        if include_comments:
            try:
                all_comments = list(post.get_comments())
                sorted_comments = sorted(
                    all_comments, key=lambda c: c.likes_count, reverse=True
                )[:5]
                comments_sample = [
                    {"text": c.text[:500], "likes": c.likes_count}
                    for c in sorted_comments
                ]
            except Exception:
                comments_sample = []

        return {
            "shortcode": shortcode,
            "date": post_date.isoformat(),
            "caption": (post.caption or "")[:1000],
            "likes": post.likes,
            "comments_count": post.comments,
            "comments_sample": comments_sample,
            "url": f"https://instagram.com/p/{shortcode}",
            "is_video": post.is_video,
        }

    async def _scrape_posts(self, shortcodes: List[str], date_from: datetime,
                            date_to: datetime, include_comments: bool,
                            username: Optional[str], password: Optional[str]) -> tuple:
        instaloader_kwargs = {"quiet": True}
        if username and password:
            instaloader_kwargs["sleep"] = True

        tasks = []
        for sc in shortcodes[:30]:
            tasks.append(self._scrape_post(
                sc, date_from, date_to, include_comments, instaloader_kwargs
            ))
            await asyncio.sleep(0.3)

        results = await asyncio.gather(*tasks)
        posts = [r for r in results if r is not None]
        errors = [sc for sc, r in zip(shortcodes[:30], results) if r is None]

        return posts, errors

    async def _analyze_emotions(self, posts: List[Dict], issue: str) -> Dict:
        if not posts:
            return {"emotions": {}, "dominant_tone": "no_data",
                    "evidence": [], "trend_summary": "Tidak ada post untuk dianalisis."}

        llm = get_llm_client()

        post_texts = []
        for p in posts[:10]:
            caption = p.get("caption", "")[:600]
            comments = p.get("comments_sample", [])
            comment_texts = [f"  kom: {c['text']} (likes {c['likes']})" for c in comments[:3]]
            block = f"<post likes={p['likes']} comments={p['comments_count']}>\n"
            block += f"  caption: {caption}\n"
            if comment_texts:
                block += "\n".join(comment_texts) + "\n"
            block += "</post>"
            post_texts.append(block)

        data_block = "\n".join(post_texts)

        prompt = (
            f"Kamu adalah analis opini publik. Analisis {len(posts)} post Instagram "
            f"tentang isu: '{issue}'.\n\n"
            f"Data post (sorted by engagement):\n{data_block}\n\n"
            "Hitung jumlah post untuk setiap dimensi emosi ini:\n"
            "- marah: geram, kesal, frustrasi, 😡🤬\n"
            "- sedih: prihatin, memprihatinkan, 😢😭\n"
            "- khawatir: takut, was-was, gawat kalau, 😰😱\n"
            "- dukung: mantap, salut, terima kasih, ❤️👏🔥\n"
            "- kritis: pemerintah tidak becus, harus bertindak, menyalahkan\n"
            "- apati: sudah biasa, gini-gini aja, pasrah\n"
            "- ajakan: ayo, tolong, laporkan, clean up\n\n"
            "Output JSON PERSIS format ini, NO markdown wrapping:\n"
            "{\n"
            '  "emotions": {"marah": N, "sedih": N, "khawatir": N, "dukung": N, '
            '"kritis": N, "apati": N, "ajakan": N},\n'
            '  "dominant_tone": "salah satu dari marah/sedih/khawatir/dukung/kritis/apati/ajakan",\n'
            '  "evidence": ["quote 1 — X likes", "quote 2 — Y likes"],\n'
            '  "trend_summary": "1-2 kalimat summary"\n'
            "}"
        )

        try:
            from openai import APIError
            res = await llm.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                timeout=30.0,
            )
            analysis = json.loads(res.choices[0].message.content or "{}")
            return analysis
        except (json.JSONDecodeError, APIError, Exception) as e:
            return {
                "emotions": {},
                "dominant_tone": "analysis_error",
                "evidence": [],
                "trend_summary": f"Gagal analisis: {str(e)[:100]}"
            }

    async def execute(self, params: InstagramMonitorInput, context: Dict[str, Any]) -> ModuleOutput:
        date_from, date_to = self._resolve_date_range(params)
        max_posts = min(params.max_posts, 30)

        try:
            search_results = await asyncio.to_thread(
                self._search_instagram_urls, params.issue, params.location_hint
            )
        except Exception as e:
            return ModuleOutput(
                status=500,
                error_msg=f"Search error: {str(e)}",
                data={"issue": params.issue},
                agent_hint=f"INSTAGRAM MONITOR: Gagal mencari data untuk '{params.issue[:60]}'.",
                thk_alignment=THKPresets.data_processing("OSINT Instagram Monitor")
            )
        shortcodes = self._extract_shortcodes(search_results)

        if not shortcodes:
            return ModuleOutput(
                status=404,
                data={
                    "issue": params.issue,
                    "period": {"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
                    "total_shortcodes_found": 0,
                    "posts": [],
                    "llm_analysis": {
                        "emotions": {}, "dominant_tone": "no_data",
                        "evidence": [], "trend_summary": "Tidak ada post Instagram ditemukan."
                    }
                },
                agent_hint=f"INSTAGRAM MONITOR: 0 post ditemukan untuk '{params.issue[:60]}'. "
                           f"Coba persingkat query atau pakai kata kunci berbeda.",
                thk_alignment=THKPresets.data_processing("OSINT Instagram Monitor")
            )

        login_user = params.instagram_login or os.getenv("INSTAGRAM_USER")
        login_pass = params.instagram_password or os.getenv("INSTAGRAM_PASS")

        posts, scrape_errors = await self._scrape_posts(
            shortcodes[:max_posts], date_from, date_to,
            params.include_comments, login_user, login_pass
        )

        total_likes = sum(p["likes"] for p in posts)
        total_comments = sum(p["comments_count"] for p in posts)

        analysis = await self._analyze_emotions(posts if params.include_comments else
                                                 [dict(p, comments_sample=[]) for p in posts],
                                                 params.issue)

        scrape_summary = {
            "total_shortcodes_found": len(shortcodes),
            "total_posts_scraped": len(posts),
            "total_posts_out_of_range": max(0, len(shortcodes[:max_posts]) - len(posts) - len(scrape_errors)),
            "total_scrape_errors": len(scrape_errors),
            "total_likes": total_likes,
            "total_comments": total_comments,
            "avg_likes_per_post": round(total_likes / len(posts), 1) if posts else 0,
            "avg_comments_per_post": round(total_comments / len(posts), 1) if posts else 0,
        }

        dominant = analysis.get("dominant_tone", "unknown")
        hint_parts = [
            f"INSTAGRAM MONITOR: {len(posts)} post tentang '{params.issue[:50]}'.",
            f"Emosi dominan: {dominant}.",
        ]
        if scrape_errors:
            hint_parts.append(f"{len(scrape_errors)} post gagal di-scrape.")

        return ModuleOutput(
            status=200,
            data={
                "issue": params.issue,
                "period": {"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
                "scrape_summary": scrape_summary,
                "posts": posts[:max_posts],
                "llm_analysis": analysis,
                "scrape_errors": scrape_errors if scrape_errors else None,
            },
            agent_hint=" ".join(hint_parts),
            thk_alignment=THKPresets.data_processing("OSINT Instagram Monitor (Instaloader + DeepSeek)")
        )


module = OSINTInstagramMonitor()
