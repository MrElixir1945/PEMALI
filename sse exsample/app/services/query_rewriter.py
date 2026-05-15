import logging
import json
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class QueryRewriter:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY
        )
        self.model = "google/gemma-3-27b-it"

    async def rewrite(self, chat_history: str, current_query: str) -> dict:
        prompt = f"""Kamu adalah mesin analisis query untuk sistem RAG pendidikan.

History: {chat_history}
User: {current_query}

TUGAS:
1. Tentukan 'intent':
   - "SUMMARY": Ringkasan keseluruhan buku/dokumen.
   - "SEARCH": Mencari penjelasan materi/konsep tertentu.
   - "QUESTIONS": User minta soal latihan.
   - "NOTES": User minta catatan/poin penting.
   - "CHAT": Sapaan, basa-basi, keluhan non-akademik (halo, capek, pusing, dll).

2. Isi 'optimized_query':
   - Untuk SEARCH, QUESTIONS, NOTES → ekstrak KEYWORD TOPIK SAJA. Singkat, padat, tanpa kata kerja instruksi. Resolusi anafora dari History jika ada kata ganti (ini/itu/tadi).
     Contoh: query "jelaskan lebih detail dong" + history topik fotosintesis → "fotosintesis"
     Contoh: query "buatkan soal tentang itu" + history topik mitosis → "mitosis pembelahan sel"
     Contoh: query "jelaskan sistem pencernaan" → "sistem pencernaan manusia"
   - Untuk SUMMARY dan CHAT → isi string kosong "".

3. Jika user sebut rentang halaman (hal 22-25, page 10-15) → isi 'page_range' dengan [start, end]. Jika tidak → null.

OUTPUT WAJIB JSON SAJA, TANPA MARKDOWN:
{{
    "intent": "...",
    "optimized_query": "...",
    "page_range": null
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=150
            )
            raw_text = response.choices[0].message.content.strip()

            # Bersihkan markdown formatting jika AI ngeyel
            if "```" in raw_text:
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()

            result = json.loads(raw_text)

            # Validasi key wajib ada
            if "intent" not in result or "optimized_query" not in result:
                raise ValueError(f"Missing required keys: {result}")

            logger.info(f"[Rewriter] Result: {result}")
            return result

        except Exception as e:
            logger.error(f"[Rewriter] Failed: {e}")
            return {"intent": "SEARCH", "optimized_query": current_query, "page_range": None}