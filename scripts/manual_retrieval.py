import chromadb
from app.config import settings
from app.embedder import embed_text
from app.ingest import CHUNKER_VERSION

client = chromadb.PersistentClient(path=settings.CHROMA_DIR)

col = client.get_collection(f"rag_{CHUNKER_VERSION}")

print(f"Total chunks in rag_{CHUNKER_VERSION}: {col.count()}")
print()

QUERIES = [
    "how does JWT authentication work",
    "where is the place order endpoint",
    "watchlist duplicate prevention",
    "how does the seller view top profit products",
    "what is the global exception handler",
]

for q in QUERIES:
    print(f"\n{'=' * 70}")
    print(f"QUERY: {q}")
    print('=' * 70)

    query_emb = embed_text(q)
    results = col.query(
        query_embeddings=[query_emb],
        n_results=5,
        include=["documents", "metadatas", "distances"],
    )

    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        dist = results["distances"][0][i]
        doc = results["documents"][0][i]
        print(f"  [{i+1}] dist={dist:.4f}  {meta.get('source_path', '?')}")
        print(f"      layer={meta.get('layer')}, role={meta.get('role_scope')}, class={meta.get('class_name')}, type={meta.get('chunk_type')}")
        if meta.get('method_name'):
            print(f"      method={meta.get('method_name')}, http={meta.get('http_method')}, endpoint={meta.get('endpoint_path')}")
        print(f"      content: {doc[:150]!r}")

