import chromadb
from chromadb.config import Settings

# Init local persist
client = chromadb.PersistentClient(path="./chroma_db")

# Create/Get collection
collection = client.get_or_create_collection(name="pemali_audit_logs")

# Test Ingest
collection.add(
    documents=["Hutan Bedugul mengalami deforestasi 15% bulan ini."],
    metadatas=[{"session_id": "test_01", "type": "observation"}],
    ids=["doc_1"]
)

# Test Query
results = collection.query(
    query_texts=["Ada kerusakan hutan?"],
    n_results=1
)

print("Status: OK")
print("Retrieved:", results["documents"])