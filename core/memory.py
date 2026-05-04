import os
import chromadb
from chromadb.config import Settings
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from typing import Dict, Any, List

# --- PostgreSQL Setup (Raw Store) ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:pemalipass@localhost/pemali_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class RawSensorData(Base):
    __tablename__ = "raw_sensor_data"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    tool_name = Column(String, index=True)
    raw_payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# --- ChromaDB Setup (Semantic Store) ---
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(allow_reset=True))

# Gunakan collection default untuk audit
try:
    audit_collection = chroma_client.get_collection("pemali_audit_logs")
except ValueError:
    audit_collection = chroma_client.create_collection("pemali_audit_logs")

# --- Interface Functions ---

def ingest_raw_data(session_id: str, tool_name: str, payload: Dict[str, Any]) -> bool:
    """Menyimpan data kuantitatif dari eksekusi tool ke PostgreSQL."""
    db = SessionLocal()
    try:
        new_record = RawSensorData(
            session_id=session_id,
            tool_name=tool_name,
            raw_payload=payload
        )
        db.add(new_record)
        db.commit()
        return True
    except Exception as e:
        print(f"[Memory Layer] Error ingesting raw data: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def store_semantic_memory(session_id: str, text_content: str, metadata: Dict[str, Any] = None) -> bool:
    """Menyimpan analisis kualitatif (narasi/reasoning) ke Vector DB."""
    if metadata is None:
        metadata = {}
    
    metadata["session_id"] = session_id
    metadata["timestamp"] = datetime.utcnow().isoformat()
    
    try:
        # ID dibuat kombinasi session dan timestamp agar unik
        doc_id = f"{session_id}_{int(datetime.utcnow().timestamp())}"
        audit_collection.add(
            documents=[text_content],
            metadatas=[metadata],
            ids=[doc_id]
        )
        return True
    except Exception as e:
        print(f"[Memory Layer] Error storing semantic memory: {e}")
        return False

def query_semantic(query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """Hybrid RAG: Mencari memori historis berdasarkan kemiripan makna."""
    try:
        results = audit_collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
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
        print(f"[Memory Layer] RAG Query error: {e}")
        return []