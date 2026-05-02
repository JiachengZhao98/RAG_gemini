import chromadb
from app.config import settings
from collections import Counter

client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
col = client.get_collection("rag_v2")

# pull all metadata
res = col.get(include=["metadatas"])

# count chunk types
chunk_types = Counter(m.get("chunk_type") for m in res["metadatas"])
print("chunk_type distribution:")
for t, n in chunk_types.most_common():
    print(f"  {t:20} {n}")

# count file_types
file_types = Counter(m.get("file_type") for m in res["metadatas"])
print("\nfile_type distribution:")
for t, n in file_types.most_common():
    print(f"  {t:20} {n}")

# count chunks per layer
layers = Counter(m.get("layer") for m in res["metadatas"])
print("\nlayer distribution:")
for t, n in layers.most_common():
    print(f"  {str(t):20} {n}")

# how many V2 chunks have endpoint_path filled?
with_endpoint = sum(1 for m in res["metadatas"] if m.get("endpoint_path"))
print(f"\nchunks with endpoint_path: {with_endpoint}")

# how many have method_name?
with_method = sum(1 for m in res["metadatas"] if m.get("method_name"))
print(f"chunks with method_name: {with_method}")

