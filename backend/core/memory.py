import os
import logging
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from backend.core.database import SessionLocal, RawSensorData, MemoryNode, MemoryEdge, get_utc_now
from typing import Dict, Any, List

CHROMA_PATH = os.getenv("CHROMA_PATH", os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "chroma_db"
))
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(allow_reset=False))

multilingual_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)
logging.info(f"[RAG] Embedding model loaded: paraphrase-multilingual-MiniLM-L12-v2")

audit_collection = chroma_client.get_or_create_collection(
    name="pemali_audit_logs",
    embedding_function=multilingual_ef
)
logging.info(f"[RAG] ChromaDB collection 'pemali_audit_logs' ready at {CHROMA_PATH}")

def ingest_raw_data(session_id: str, tool_name: str, payload: Dict[str, Any]) -> bool:
    db = SessionLocal()
    try:
        new_record = RawSensorData(session_id=session_id, tool_name=tool_name, raw_payload=payload)
        db.add(new_record)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logging.error(f"[Memory Layer] Ingest Error: {str(e)}") # Fixed: Silent failure
        return False
    finally:
        db.close()

def store_semantic_memory(session_id: str, text_content: str, metadata: Dict[str, Any] = None) -> bool:
    metadata = metadata or {}
    metadata["session_id"] = session_id
    metadata["timestamp"] = get_utc_now().isoformat()
    
    try:
        doc_id = f"{session_id}_{int(get_utc_now().timestamp())}"
        audit_collection.add(documents=[text_content], metadatas=[metadata], ids=[doc_id])
        return True
    except Exception as e:
        logging.error(f"[Memory Layer] RAG Store Error: {str(e)}") # Fixed: Silent failure
        return False

def query_semantic(query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
    try:
        results = audit_collection.query(query_texts=[query_text], n_results=n_results)
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
        return formatted_results
    except Exception as e:
        logging.error(f"[Memory Layer] RAG Query Error: {str(e)}")
        return []

# ============================================================
# KNOWLEDGE GRAPH CRUD
# ============================================================

def insert_memory_graph(session_id: str, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Insert nodes and edges into the knowledge graph atomically."""
    db = SessionLocal()
    label_to_id = {}
    created_nodes = []
    created_edges = []
    
    try:
        # Insert nodes
        for node_data in nodes:
            node = MemoryNode(
                node_type=node_data.get("node_type", "unknown"),
                label=node_data.get("label", "unnamed"),
                properties=node_data.get("properties", {}),
                session_id=session_id
            )
            db.add(node)
            db.flush()  # get ID without committing
            label_to_id[node_data["label"]] = node.id
            created_nodes.append(node.id)
        
        # Insert edges
        for edge_data in edges:
            edge = MemoryEdge(
                source_label=edge_data.get("source_label", ""),
                target_label=edge_data.get("target_label", ""),
                relation_type=edge_data.get("relation_type", "unknown"),
                temporal_context=edge_data.get("temporal_context", {}),
                weight=edge_data.get("weight", 0),
                memory_node_id=label_to_id.get(edge_data.get("memory_node_id", edge_data.get("source_label", 0)), 0)
            )
            db.add(edge)
            created_edges.append(edge.id if hasattr(edge, 'id') else None)
        
        db.commit()
        
        return {
            "status": "success",
            "nodes_created": len(created_nodes),
            "edges_created": len(created_edges),
            "node_ids": created_nodes,
            "edge_ids": created_edges
        }
    except Exception as e:
        db.rollback()
        logging.error(f"[Memory Layer] Knowledge Graph Insert Error: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "nodes_created": 0,
            "edges_created": 0
        }
    finally:
        db.close()


def query_memory_graph(query: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """Query memory nodes by label similarity (simple keyword search for MVP)."""
    db = SessionLocal()
    try:
        results = db.query(MemoryNode).filter(
            MemoryNode.label.ilike(f"%{query}%")
        ).order_by(MemoryNode.last_updated.desc()).limit(n_results).all()
        
        return [
            {
                "id": r.id,
                "label": r.label,
                "node_type": r.node_type,
                "properties": r.properties,
                "session_id": r.session_id,
                "last_updated": r.last_updated.isoformat() if r.last_updated else None
            }
            for r in results
        ]
    except Exception as e:
        logging.error(f"[Memory Layer] Knowledge Graph Query Error: {str(e)}")
        return []
    finally:
        db.close()


def get_memory_graph_for_session(session_id: str) -> Dict[str, Any]:
    """Get all nodes and edges for a specific audit session."""
    db = SessionLocal()
    try:
        nodes = db.query(MemoryNode).filter(MemoryNode.session_id == session_id).all()
        node_ids = [n.id for n in nodes]
        
        edges = db.query(MemoryEdge).filter(
            MemoryEdge.memory_node_id.in_(node_ids)
        ).all() if node_ids else []
        
        return {
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "node_type": n.node_type,
                    "properties": n.properties
                }
                for n in nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source_label,
                    "target": e.target_label,
                    "relation": e.relation_type,
                    "weight": e.weight
                }
                for e in edges
            ]
        }
    except Exception as e:
        logging.error(f"[Memory Layer] Session Graph Query Error: {str(e)}")
        return {"nodes": [], "edges": []}
    finally:
        db.close()