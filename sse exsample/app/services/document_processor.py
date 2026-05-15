"""
Document Processor Service
==========================
VLM-based PDF extraction and chunking

Architecture: Full Vision-to-Markdown + Parent-Child Chunking
"""

import os
import logging
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
from io import BytesIO

import re
import fitz  # PyMuPDF
from PIL import Image
from tqdm import tqdm
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_offset_from_filename(filename: str) -> int:
    """Extract page offset from filename pattern (_offset12, _start13, etc.)."""
    import re
    match = re.search(r'_offset(\d+)', filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match_start = re.search(r'_start(\d+)', filename, re.IGNORECASE)
    if match_start:
        return int(match_start.group(1)) - 1
    return 0


class DocumentProcessor:
    """
    VLM-based document processor:
    1. Converts PDF pages to images (150 DPI)
    2. Extracts Markdown via Qwen3-VL-235B
    3. Creates Parent-child chunks with table protection
    """

    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 300):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        api_key = settings.OPENROUTER_API_KEY

        self.client = OpenAI(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=api_key
        )
        self.model_name = settings.VLM_MODEL
        logger.info(f"☁️ Cloud Processor Initialized: {self.model_name}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        reraise=True
    )
    def _extract_markdown_via_vlm(self, img_b64: str) -> str:
        """Core VLM Engine: Converts raw image to clean Markdown."""
        prompt = """You are an expert academic document extraction engine.
Your task is to transcribe this image into structured, semantic Markdown.

STRICT RULES:
1.  **NO CONVERSATION:** Output ONLY the raw Markdown text.
2.  **PAGE NUMBER:** Look for the physical printed page number on the page (usually at the corners). You MUST output it on the VERY FIRST LINE of your response wrapped in tags: <page>12</page>. If it's a roman numeral, output <page>iv</page>. If there is NO visible page number, output <page>UNKNOWN</page>.
3.  **TABLES:** Preserve all tables EXACTLY using standard Markdown table syntax.
4.  **MATHEMATICS:** Convert ALL mathematical formulas to standard LaTeX format. Use $ for inline and $$ for block math.
5.  **DIAGRAMS:** Describe physical/geometry diagrams concisely inside square brackets [Diagram: ...].
6.  **CLEANUP:** Ignore watermarks, headers, and footers. Extract the core academic content."""

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]
            }],
            temperature=0.1,
            max_tokens=2000
        )
        return response.choices[0].message.content.strip()

    def chunk_markdown_structurally(self, markdown_text: str) -> List[str]:
        """
        Splits markdown logically dengan overlap + table protection.
        """
        if len(markdown_text) < 50 or "I cannot fulfill" in markdown_text or "As an AI" in markdown_text:
            logger.warning("⚠️ VLM output validation failed.")
            return [markdown_text]

        blocks = markdown_text.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0

        for block in blocks:
            block_len = len(block)
            is_table = block.strip().startswith("|") and "\n|" in block

            if is_table and block_len > self.chunk_size:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk).strip())
                chunks.append(block.strip())
                current_chunk = []
                current_length = 0
                continue

            if current_length + block_len > self.chunk_size and current_length > 0:
                chunks.append("\n\n".join(current_chunk).strip())

                overlap_chunk = []
                overlap_length = 0
                for prev_block in reversed(current_chunk):
                    if overlap_length + len(prev_block) <= self.chunk_overlap:
                        overlap_chunk.insert(0, prev_block)
                        overlap_length += len(prev_block) + 2
                    else:
                        break

                current_chunk = overlap_chunk + [block]
                current_length = overlap_length + block_len
            else:
                current_chunk.append(block)
                current_length += block_len + 2

        if current_chunk:
            chunks.append("\n\n".join(current_chunk).strip())

        return chunks




    def _process_single_page(self, pdf_path: str, page_index: int, page_offset: int, filename: str) -> List[Dict]:
        """Helper untuk memproses 1 halaman secara isolated (Thread-safe)"""
        fallback_page = (page_index + 1) - page_offset # Tetap simpan sebagai cadangan
        child_chunks = []
        
        doc_fitz = fitz.open(pdf_path)
        try:
            pix = doc_fitz[page_index].get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_b64 = base64.b64encode(buffered.getvalue()).decode()

            raw_markdown = self._extract_markdown_via_vlm(img_b64)
            if not raw_markdown.strip():
                return []

            # --- START LOGIC EKSTRAKSI HALAMAN ---
            detected_page = str(fallback_page)
            page_match = re.search(r'<page>(.*?)</page>', raw_markdown, re.IGNORECASE)
            
            if page_match:
                val = page_match.group(1).strip()
                if val.upper() != "UNKNOWN" and val != "":
                    detected_page = val # Pakai angka yang dilihat VLM
            
            # Hapus tag <page> dari markdown agar teksnya bersih
            clean_markdown = re.sub(r'<page>.*?</page>\n*', '', raw_markdown, flags=re.IGNORECASE).strip()
            # --- END LOGIC EKSTRAKSI HALAMAN ---

            child_texts = self.chunk_markdown_structurally(clean_markdown)
            parent_id = f"doc_{filename}_page_{detected_page}" # Gunakan detected_page

            for chunk_idx, child_text in enumerate(child_texts):
                child_chunks.append({
                    "text": f"[Sub-bagian Hal {detected_page}]\n{child_text}",
                    "metadata": {
                        "source": filename,
                        "page": str(detected_page), # Masukkan ke metadata
                        "chunk_id": f"{parent_id}_chunk_{chunk_idx}",
                        "parent_id": parent_id,
                        "parent_text": clean_markdown,
                        "has_visual": True if "|" in child_text else False
                    }
                })
        except Exception as e:
            logger.error(f"Failed processing page index {page_index}: {e}")
        finally:
            doc_fitz.close()
            
        return child_chunks

    def process_pdf_multimodal(
        self,
        pdf_path: str,
        page_offset: int = 0,
        original_filename: str = None
    ) -> List[Dict[str, Any]]:
        """Process PDF dengan VLM extraction secara Paralel."""
        
        # ---> UBAH BARIS INI <---
        filename = original_filename if original_filename else Path(pdf_path).name
        
        if page_offset == 0:
            page_offset = get_offset_from_filename(filename)

        logger.info(f"🚀 VLM Parallel Ingestion Started: {filename} [Offset={page_offset}]")

        # Buka sebentar cuma untuk ngitung total halaman
        doc_fitz = fitz.open(pdf_path)
        total_pages = len(doc_fitz)
        doc_fitz.close()

        all_child_chunks = []

        # PARALLEL EXECUTION: Proses 5 halaman sekaligus
        max_workers = 5 
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Daftarkan semua halaman ke antrean pekerja
            futures = {
                executor.submit(self._process_single_page, pdf_path, i, page_offset, filename): i 
                for i in range(total_pages)
            }
            
            # Tunggu dan kumpulkan hasilnya pakai tqdm biar loading bar-nya tetep jalan
            for future in tqdm(as_completed(futures), total=total_pages, desc="VLM Parallel Pages"):
                result = future.result()
                if result:
                    all_child_chunks.extend(result)

        logger.info(f"✅ Finished: Extracted {len(all_child_chunks)} chunks.")
        return all_child_chunks

    def process_uploaded_file(
        self,
        file_path: str,
        doc_id: str,
        user_id: str,
        original_filename: str  # ← FIXED: inject user_id
    ) -> List[Dict[str, Any]]:
        """
        Process uploaded file, inject doc_id + user_id ke semua chunks.

        Args:
            file_path: Path to uploaded PDF
            doc_id: Document ID dari database
            user_id: User ID yang upload dokumen  ← BARU

        Returns:
            List of chunks dengan doc_id + user_id di metadata
        """
        filename = Path(file_path).name
        logger.info(f"Processing: {filename} [DocID: {doc_id}] [UserID: {user_id}]")

        chunks = self.process_pdf_multimodal(file_path)

        for chunk in chunks:
            chunk["metadata"]["doc_id"] = doc_id
            chunk["metadata"]["user_id"] = user_id  # ← FIXED
            chunk["metadata"]["source"] = original_filename

        return chunks


class DocumentService:
    """Service layer untuk document processing."""

    def __init__(self):
        self.processor = DocumentProcessor()

    def process_and_index(
        self,
        doc_id: str,
        user_id: str,  # ← FIXED: tambah user_id
        file_path: str,
        original_filename: str,
        db_session=None,
        rag_service=None
    ) -> Dict[str, Any]:
        """
        Process document dan index ke RAG service.
        """
        logger.info(f"Starting processing: doc_id={doc_id} user_id={user_id}")

        try:
            # Process PDF dengan VLM
            chunks = self.processor.process_uploaded_file(
                file_path=file_path,
                doc_id=doc_id,
                user_id=user_id,  # ← FIXED
                original_filename=original_filename
            )

            # Index ke Qdrant
            if rag_service:
                rag_service.index_documents(
                    user_id=user_id,  # ← FIXED
                    doc_id=doc_id,
                    chunks=chunks
                )

            # Update DB
            if db_session:
                from app.db.models import Document
                from datetime import datetime, timezone
                doc = db_session.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    doc.total_chunks = len(chunks)
                    doc.status = "completed"
                    doc.processed_at = datetime.now(timezone.utc)
                    db_session.commit()

            return {
                "doc_id": doc_id,
                "status": "completed",
                "total_chunks": len(chunks),
                "error_message": None
            }

        except Exception as e:
            logger.error(f"Document processing failed: {e}")

            if db_session:
                from app.db.models import Document
                doc = db_session.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    doc.status = "failed"
                    db_session.commit()

            return {
                "doc_id": doc_id,
                "status": "failed",
                "total_chunks": 0,
                "error_message": str(e)
            }
