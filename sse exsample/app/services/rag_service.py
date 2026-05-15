"""
RAG Service Module
==================
RAG pipeline dengan Qdrant vector DB + BGE-M3 hybrid search.

Architecture:
- Embedding: BAAI/bge-m3 (dense + sparse)
- Vector DB: Qdrant (persistent, filter by user_id)
- Search: Hybrid dense + sparse via Qdrant
- Reranker: Cross-encoder mmarco (optional, toggle USE_RERANKER)
- Parent-Child: child di-search, parent di-return ke prompt
"""
import math
import logging
import uuid
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum

from FlagEmbedding import BGEM3FlagModel, FlagReranker
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.models import (
    Distance,
    VectorParams,
    SparseVectorParams,
    SparseIndexParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    SearchRequest,
    NamedVector,
    NamedSparseVector,
    SparseVector,
    Prefetch,
    FusionQuery,
    Fusion,
)

from app.core.config import settings
from app.services.query_rewriter import QueryRewriter

logger = logging.getLogger(__name__)

COLLECTION_NAME = "sismind_chunks"


# ==============================================================================
# Query Type Detection
# ==============================================================================

class QueryType(Enum):
    SIMPLE = "simple"
    COMPARISON = "comparison"
    MULTI_TOPIC = "multi_topic"
    DETAILED = "detailed"


class QueryAnalyzer:
    """Query type detection menggunakan heuristics."""

    COMPARISON_KEYWORDS = [
        'bandingkan', 'versus', 'vs', 'bedanya', 'perbedaan',
        'dibanding', 'lebih baik', 'mana yang'
    ]

    MULTI_TOPIC_KEYWORDS = [
        'hubungan', 'pengaruh', 'dampak', 'akibat',
        'keterkaitan', 'efek', 'implikasi'
    ]

    DETAIL_KEYWORDS = [
        'jelaskan', 'bagaimana', 'mengapa', 'analisis',
        'uraikan', 'diskusikan', 'evaluasi'
    ]

    def analyze(self, query: str) -> Tuple[QueryType, int]:
        """
        Analyze query dan return type + optimal n_results.

        Returns:
            Tuple of (query_type, n_results)
        """
        query_lower = query.lower()
        word_count = len(query.split())

        is_comparison = any(w in query_lower for w in self.COMPARISON_KEYWORDS)
        has_multiple = ' dan ' in query_lower and (
            query_lower.count(' dan ') > 1 or
            any(kw in query_lower for kw in ['hubungan', 'keterkaitan'])
        )
        is_relationship = any(w in query_lower for w in self.MULTI_TOPIC_KEYWORDS)
        wants_detail = any(w in query_lower for w in self.DETAIL_KEYWORDS)

        # [TUNING #1] Naikkan semua n_results agar Armisa punya lebih banyak bahan
        if word_count < 8 and not is_comparison and not has_multiple:
            if wants_detail:
                return QueryType.DETAILED, 15  # <-- Sebelumnya 12
            return QueryType.SIMPLE, 8         # <-- Sebelumnya 6
        elif is_comparison:
            return QueryType.COMPARISON, 20    # <-- Sebelumnya 15
        elif is_relationship or has_multiple:
            return QueryType.MULTI_TOPIC, 16   # <-- Sebelumnya 12
        elif word_count > 15:
            return QueryType.DETAILED, 20      # <-- Sebelumnya 15
        else:
            return QueryType.DETAILED, 15      # <-- Sebelumnya 10

# ==============================================================================
# BGE-M3 Encoder
# ==============================================================================

class BGEM3Encoder:
    """
    Wrapper untuk BGE-M3 model.
    Lazy loading — model di-load saat pertama kali dipakai.
    """

    def __init__(self):
        self._model: Optional[BGEM3FlagModel] = None

    @property
    def model(self) -> BGEM3FlagModel:
        if self._model is None:
            logger.info(f"Loading BGE-M3 model: {settings.EMBEDDING_MODEL}")
            self._model = BGEM3FlagModel(
                settings.EMBEDDING_MODEL,
                use_fp16=True
            )
            logger.info("BGE-M3 loaded successfully")
        return self._model

    def encode_query(self, query: str) -> Dict:
        """
        Encode query untuk search.
        BGE-M3 butuh prefix 'query: ' untuk retrieval task.
        """
        output = self.model.encode(
            [f"query: {query}"],
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False
        )
        return {
            "dense": output["dense_vecs"][0].tolist(),
            "sparse": self._to_sparse_dict(output["lexical_weights"][0])
        }

    def encode_passages(self, texts: List[str]) -> List[Dict]:
        """
        Encode dokumen/passages untuk indexing.
        BGE-M3 butuh prefix 'passage: ' untuk passages.
        """
        prefixed = [f"passage: {t}" for t in texts]
        output = self.model.encode(
            prefixed,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
            batch_size=8
        )

        results = []
        for i in range(len(texts)):
            results.append({
                "dense": output["dense_vecs"][i].tolist(),
                "sparse": self._to_sparse_dict(output["lexical_weights"][i])
            })
        return results

    def _to_sparse_dict(self, lexical_weights: Dict) -> Dict[int, float]:
        """Convert BGE-M3 lexical weights ke format Qdrant sparse vector."""
        return {int(k): float(v) for k, v in lexical_weights.items()}


# ==============================================================================
# Reranker
# ==============================================================================

class RerankerService:
    """
    Cross-encoder reranker wrapper.
    Lazy loading — model di-load saat pertama kali dipakai.
    Toggle via settings.USE_RERANKER.
    """

    def __init__(self):
        self._model: Optional[FlagReranker] = None

    @property
    def model(self) -> FlagReranker:
        if self._model is None:
            logger.info(f"Loading reranker model: {settings.RERANKER_MODEL}")
            self._model = FlagReranker(
                settings.RERANKER_MODEL,
                use_fp16=True
            )
            logger.info("Reranker loaded successfully")
        return self._model

    def rerank(self, query: str, results: List[Dict], threshold: float = 0.3) -> List[Dict]:
        """
        Rerank search results menggunakan cross-encoder dengan Similarity Threshold.

        Args:
            query: Original search query
            results: List of search result dicts (harus punya key 'content')
            threshold: Minimum relevance score (0.0-1.0). Chunk di bawah ini dibuang.

        Returns:
            Top RERANK_FINAL_TOP_K results yang lolos threshold, sorted by score descending
        """
        if not results:
            return results

        # Buat pairs [query, content] untuk cross-encoder
        pairs = [[query, r["content"]] for r in results]

        raw_scores = self.model.compute_score(pairs)
        if isinstance(raw_scores, float):
            raw_scores = [raw_scores]

        # Normalize manual via sigmoid (menghasilkan skor 0.0 sampai 1.0)
        scores = [1 / (1 + math.exp(-s)) for s in raw_scores]

        # Handle single result
        if isinstance(scores, float):
            scores = [scores]

        # Attach reranker score ke results
        for result, score in zip(results, scores):
            result["reranker_score"] = float(score)

        # ==========================================================
        # FILTERING THRESHOLD UNTUK BUKU TEBAL
        # Buang semua chunk yang relevansinya di bawah batas (default 30%)
        # ==========================================================
        filtered_results = [r for r in results if r["reranker_score"] >= threshold]

        # Sort by reranker score, ambil top K
        reranked = sorted(filtered_results, key=lambda x: x["reranker_score"], reverse=True)
        top_k = reranked[:settings.RERANK_FINAL_TOP_K]

        if top_k:
            logger.info(
                f"Reranked {len(results)} awal → Lolos threshold({threshold}): {len(filtered_results)} "
                f"→ Diambil Top: {len(top_k)}. Top score: {top_k[0]['reranker_score']:.4f}"
            )
        else:
            logger.warning(
                f"Reranked {len(results)} awal → 0 chunk lolos threshold({threshold}). "
                "Pertimbangkan turunkan threshold."
            )
        return top_k


# ==============================================================================
# Qdrant Manager
# ==============================================================================

class QdrantManager:
    """
    Manages Qdrant collection dan operasi upsert/search.
    """

    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self._ensure_collection()

    def _ensure_collection(self):
        """Buat collection kalau belum ada."""
        existing = [c.name for c in self.client.get_collections().collections]

        if COLLECTION_NAME not in existing:
            logger.info(f"Creating Qdrant collection: {COLLECTION_NAME}")
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config={
                    "dense": VectorParams(
                        size=1024,
                        distance=Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(
                        index=SparseIndexParams(on_disk=False)
                    )
                }
            )
            logger.info(f"Collection '{COLLECTION_NAME}' created")
        else:
            logger.info(f"Collection '{COLLECTION_NAME}' already exists")

    def upsert_chunks(
        self,
        chunks: List[Dict],
        user_id: str,
        doc_id: str,
        encoder: BGEM3Encoder
    ):
        """
        Upsert chunks ke Qdrant dengan user_id + doc_id di payload.
        """
        if not chunks:
            logger.warning("No chunks to upsert")
            return

        logger.info(f"Encoding {len(chunks)} chunks for user={user_id} doc={doc_id}")

        texts = [c["text"] for c in chunks]
        embeddings = encoder.encode_passages(texts)

        points = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            metadata = chunk.get("metadata", {})

            point = PointStruct(
                id=str(uuid.uuid4()),
                vector={
                    "dense": emb["dense"],
                    "sparse": SparseVector(
                        indices=list(emb["sparse"].keys()),
                        values=list(emb["sparse"].values())
                    )
                },
                payload={
                    "user_id": user_id,
                    "doc_id": doc_id,
                    "content": chunk["text"],
                    "source": metadata.get("source", ""),
                    "page": metadata.get("page", ""),
                    "chunk_id": metadata.get("chunk_id", ""),
                    "parent_id": metadata.get("parent_id", ""),
                    "parent_text": metadata.get("parent_text", chunk["text"]),
                    "has_visual": metadata.get("has_visual", False),
                }
            )
            points.append(point)

        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=COLLECTION_NAME,
                points=batch
            )
            logger.info(f"Upserted batch {i//batch_size + 1}, {len(batch)} points")

        logger.info(f"✅ Upserted {len(points)} chunks for doc={doc_id}")

    def hybrid_search(
        self,
        query_dense: List[float],
        query_sparse: Dict[int, float],
        user_id: str,
        n_results: int = 20,
        doc_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Hybrid search (dense + sparse) dengan filter user_id atau doc_ids.

        Args:
            query_dense: Dense vector dari BGE-M3
            query_sparse: Sparse vector dari BGE-M3
            user_id: Fallback filter kalau doc_ids tidak di-set
            n_results: Jumlah hasil
            doc_ids: Optional filter by specific documents (support multi-doc).
                     Kalau di-set, user_id DIABAIKAN — cocok untuk Global Docs.
        """
        # ==========================================================
        # FIX: Filter logic baru — doc_ids takes priority over user_id
        # Ini yang bikin Global Docs (milik admin) bisa ke-search oleh user lain
        # ==========================================================
        must_conditions = []

        if doc_ids:
            # Cari strictly di dokumen yang dipilih, abaikan user_id
            # (support Global Docs yang di-upload admin/orang lain)
            if len(doc_ids) == 1:
                must_conditions.append(
                    models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_ids[0]))
                )
            else:
                must_conditions.append(
                    models.FieldCondition(key="doc_id", match=models.MatchAny(any=doc_ids))
                )
        else:
            # Fallback: cari semua dokumen private milik user ini
            must_conditions.append(
                models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))
            )

        search_filter = models.Filter(must=must_conditions) if must_conditions else None
        # ==========================================================

        results = self.client.query_points(
            collection_name=COLLECTION_NAME,
            prefetch=[
                Prefetch(
                    query=query_dense,
                    using="dense",
                    limit=n_results,
                    filter=search_filter
                ),
                Prefetch(
                    query=SparseVector(
                        indices=list(query_sparse.keys()),
                        values=list(query_sparse.values())
                    ),
                    using="sparse",
                    limit=n_results,
                    filter=search_filter
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=n_results,
            with_payload=True
        )

        return [
            {
                "id": str(r.id),
                "content": r.payload.get("content", ""),
                "metadata": {
                    "source": r.payload.get("source", ""),
                    "page": r.payload.get("page", ""),
                    "chunk_id": r.payload.get("chunk_id", ""),
                    "parent_id": r.payload.get("parent_id", ""),
                    "parent_text": r.payload.get("parent_text", ""),
                    "has_visual": r.payload.get("has_visual", False),
                    "doc_id": r.payload.get("doc_id", ""),
                },
                "score": r.score
            }
            for r in results.points
        ]

    def scroll_chunks_by_filter(
        self,
        must_conditions: List[models.Condition],
        limit: int = 15
    ) -> List[Dict]:
        """Bypass Vector Search: Tarik chunks langsung pakai filter SQL-style (untuk intent SUMMARY/RANGE)."""
        results, _ = self.client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(must=must_conditions),
            limit=limit,
            with_payload=True
        )
        return [
            {
                "id": str(r.id),
                "content": r.payload.get("content", ""),
                "metadata": {
                    "source": r.payload.get("source", ""),
                    "page": r.payload.get("page", ""),
                    "chunk_id": r.payload.get("chunk_id", ""),
                    "parent_id": r.payload.get("parent_id", ""),
                    "parent_text": r.payload.get("parent_text", ""),
                    "has_visual": r.payload.get("has_visual", False),
                    "doc_id": r.payload.get("doc_id", ""),
                },
                "score": 1.0  # Default score karena tidak ada perhitungan vektor
            }
            for r in results
        ]

    def delete_document(self, user_id: str, doc_id: str):
        """Hapus semua chunks milik sebuah dokumen."""
        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                    FieldCondition(key="doc_id", match=MatchValue(value=doc_id)),
                ]
            )
        )
        logger.info(f"Deleted all chunks for doc={doc_id} user={user_id}")

    def get_user_doc_ids(self, user_id: str) -> List[str]:
        """Get semua doc_id yang sudah diindex oleh user."""
        results = self.client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            ),
            with_payload=["doc_id"],
            limit=1000
        )
        doc_ids = list(set(r.payload.get("doc_id") for r in results[0] if r.payload.get("doc_id")))
        return doc_ids


# ==============================================================================
# RAG Service — Main Interface
# ==============================================================================

class RAGService:
    """
    Main RAG service interface untuk FastAPI.
    Singleton-friendly, lazy load semua heavy components.
    """

    def __init__(self):
        self._encoder: Optional[BGEM3Encoder] = None
        self._qdrant: Optional[QdrantManager] = None
        self._reranker: Optional[RerankerService] = None
        self.query_analyzer = QueryAnalyzer()
        self.rewriter = QueryRewriter()

    @property
    def encoder(self) -> BGEM3Encoder:
        if self._encoder is None:
            self._encoder = BGEM3Encoder()
        return self._encoder

    @property
    def qdrant(self) -> QdrantManager:
        if self._qdrant is None:
            self._qdrant = QdrantManager()
        return self._qdrant

    @property
    def reranker(self) -> RerankerService:
        if self._reranker is None:
            self._reranker = RerankerService()
        return self._reranker

    def index_documents(
        self,
        user_id: str,
        doc_id: str,
        chunks: List[Dict[str, Any]]
    ):
        """
        Index dokumen chunks ke Qdrant.
        """
        self.qdrant.upsert_chunks(
            chunks=chunks,
            user_id=user_id,
            doc_id=doc_id,
            encoder=self.encoder
        )

    async def search(
        self,
        user_id: str,
        query: str,
        chat_history: str = "",
        n_results: Optional[int] = None,
        doc_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Search dengan Intent Routing: CHAT, SUMMARY, SEARCH, QUESTIONS, NOTES."""

        # Step 0: Intent Routing via Gemma 3
        rewriter_result = await self.rewriter.rewrite(chat_history, query)
        intent = rewriter_result.get("intent", "SEARCH")
        optimized_query = rewriter_result.get("optimized_query", "").strip() or query
        page_range = rewriter_result.get("page_range")

        logger.info(f"[ROUTER] Intent: {intent} | Query: '{optimized_query}' | Range: {page_range}")

        # ---------------------------------------------------------
        # ROUTE 1: CHAT (Bypass Total)
        # ---------------------------------------------------------
        if intent == "CHAT":
            return {"intent": intent, "chunks": []}

        query_type, auto_n = self.query_analyzer.analyze(optimized_query)
        if n_results is None:
            n_results = auto_n

        # Siapkan filter dasar (milik user atau doc spesifik)
        base_conditions = []
        if doc_ids:
            if len(doc_ids) == 1:
                base_conditions.append(models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_ids[0])))
            else:
                base_conditions.append(models.FieldCondition(key="doc_id", match=models.MatchAny(any=doc_ids)))
        else:
            base_conditions.append(models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id)))

        # ---------------------------------------------------------
        # ROUTE 2: SUMMARY atau PAGE RANGE (Bypass Vector Search)
        # ---------------------------------------------------------
        if intent == "SUMMARY" or page_range:
            filter_conditions = list(base_conditions)

            # Logic ubah range [22, 25] jadi MatchAny string ["22","23","24","25"]
            # Karena Qdrant range filter cuma jalan di integer, tapi metadata.page kita string
            if page_range and isinstance(page_range, list) and len(page_range) == 2:
                try:
                    pages_str = [str(i) for i in range(int(page_range[0]), int(page_range[1]) + 1)]
                    filter_conditions.append(
                        models.FieldCondition(key="page", match=models.MatchAny(any=pages_str))
                    )
                except (ValueError, TypeError):
                    pass  # Abaikan jika halamannya romawi/bukan angka

            # [TUNING #2] Naikkan limit scroll agar SUMMARY/PAGE RANGE punya lebih banyak materi
            raw_results = self.qdrant.scroll_chunks_by_filter(
                must_conditions=filter_conditions,
                limit=20 if intent == "SUMMARY" else 40  # <-- Sebelumnya 15 / 30
            )

            final_chunks = self._deduplicate_by_parent(raw_results, n_results)
            return {"intent": intent, "chunks": final_chunks}

        # ---------------------------------------------------------
        # ROUTE 3: SEARCH, QUESTIONS, NOTES (Vector/Hybrid Search)
        # ---------------------------------------------------------
        encoded = self.encoder.encode_query(optimized_query)

        # [TUNING #3] Naikkan candidate_count minimum agar reranker punya lebih banyak input
        base_candidate_count = settings.RERANK_TOP_K if settings.USE_RERANKER else n_results * 4
        candidate_count = max(50, base_candidate_count)  # <-- Sebelumnya max(40, ...)

        raw_results = self.qdrant.hybrid_search(
            query_dense=encoded["dense"],
            query_sparse=encoded["sparse"],
            user_id=user_id,
            n_results=candidate_count,
            doc_ids=doc_ids
        )

        if not raw_results:
            logger.info("No results found in Qdrant")
            return {"intent": intent, "chunks": []}

        if settings.USE_RERANKER:
            filtered_results = self.reranker.rerank(query=optimized_query, results=raw_results, threshold=0.3)
            if not filtered_results and raw_results:
                logger.info("Reranker gagal tembus threshold, menggunakan top 3 dari Qdrant sebagai fallback.")
                raw_results = raw_results[:3]
            else:
                raw_results = filtered_results

        final_chunks = self._deduplicate_by_parent(raw_results, n_results)

        logger.info(f"Returning {len(final_chunks)} chunks after dedup | intent={intent}")
        return {"intent": intent, "chunks": final_chunks}

    def _deduplicate_by_parent(
        self,
        docs: List[Dict],
        n_results: int
    ) -> List[Dict]:
        """
        Dedup by parent_id, return parent_text sebagai content.
        Urutan ranking dari reranker dipertahankan.
        """
        seen_parents = set()
        unique_results = []

        for doc in docs:
            parent_id = doc.get("metadata", {}).get("parent_id")

            if not parent_id:
                unique_results.append(doc)
                continue

            if parent_id in seen_parents:
                continue

            seen_parents.add(parent_id)

            parent_text = doc.get("metadata", {}).get("parent_text") or doc["content"]

            unique_results.append({
                "id": parent_id,
                "content": parent_text,
                "metadata": doc["metadata"],
                "score": doc.get("reranker_score", doc.get("score", 0))
            })

            if len(unique_results) >= n_results:
                break

        return unique_results

    def get_query_type(self, query: str) -> str:
        """Get query type classification."""
        query_type, _ = self.query_analyzer.analyze(query)
        return query_type.value

    def delete_document(self, user_id: str, doc_id: str):
        """Hapus dokumen dari Qdrant."""
        self.qdrant.delete_document(user_id, doc_id)

    def get_user_documents(self, user_id: str) -> List[str]:
        """Get semua doc_id yang sudah diindex untuk user ini."""
        return self.qdrant.get_user_doc_ids(user_id)