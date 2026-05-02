import chromadb
import os
from pathlib import Path
from app.config import settings
from dataclasses import asdict
from app.embedder import embed_text


CHUNKER_VERSION = os.getenv("CHUNKER_VERSION", "v1")


if CHUNKER_VERSION == "v1":
    from app.chunking.chunker import chunk_text as chunker_fn
elif CHUNKER_VERSION == "v2":
    from app.chunking.chunker_v2 import chunk_java_file as chunker_fn
    from app.chunking.chunker import chunk_text as chunker_fn_v1

else:
    raise ValueError(f"Unknown CHUNKER_VERSION: {CHUNKER_VERSION}")

COLLECTION_NAME = f"rag_{CHUNKER_VERSION}"

EXCLUDE_DIRS = {"target", "build", ".git", ".idea", ".mvn", "node_modules", "__pycache__"}
EXCLUDE_EXTS = {".class", ".jar", ".war", ".png", ".jpg", ".gif", ".ico", ".pdf", ".lock"}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db", ".gitkeep"}


def get_chroma_collection():
    chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DIR)

    # delete if exists, to ensure a clean re-ingest
    try:
        chroma_client.delete_collection(name=COLLECTION_NAME)
        print(f"[reset] deleted existing collection: {COLLECTION_NAME}")
    except Exception:
        pass  # collection didn't exist, that's fine
    collection = chroma_client.create_collection(name=COLLECTION_NAME)
    return collection


def load_text_files(data_dir: str) -> list[dict]:
    documents = []
    base_path = Path(data_dir)

    for file_path in base_path.rglob("*"):

        if not file_path.is_file():
            continue
        # skip if any parent dir is in exclude list
        if any(part in EXCLUDE_DIRS for part in file_path.parts):
            continue
        if file_path.suffix.lower() in EXCLUDE_EXTS:
            continue
        if file_path.name in EXCLUDE_NAMES:
            continue

        try:
            text = file_path.read_text(encoding="utf-8").strip()
        except UnicodeDecodeError:
            print(f"[skip] non-utf8 file: {file_path}")
            continue

        documents.append({
            "text": text,
            "absolute_path": str(file_path),
            "relative_path": str(file_path.relative_to(base_path)),   # 这个是 chunker 要的
            "filename": file_path.name,
            "file_type": file_path.suffix.lstrip(".").lower(),
        })

    return documents



def ingest_documents(data_dir: str = "data"):
    documents = load_text_files(data_dir)
    collection = get_chroma_collection()

    ids = []
    embeddings = []
    metadatas = []
    texts = []

    chunk_counter = 0

    for doc in documents:
        if CHUNKER_VERSION == "v2" and doc["file_type"] != "java":
            chunks = chunker_fn_v1(doc["text"], doc["relative_path"])
        else:
            chunks = chunker_fn(doc["text"], doc["relative_path"])
        for chunk in chunks:
            content = chunk.content
            embedding = embed_text(content)
            meta_dict = asdict(chunk.metadata)

            for key in ("path_params", "query_params", "annotations", "calls", "injected_dependencies"):
                if isinstance(meta_dict.get(key), list):
                    meta_dict[key] = ", ".join(meta_dict[key]) if meta_dict[key] else ""

            # Chroma also doesn't accept None; replace with empty string or skip
            meta_dict = {k: (v if v is not None else "") for k, v in meta_dict.items()}

            ids.append(chunk.metadata.chunk_id)
            embeddings.append(embedding)
            texts.append(content)
            metadatas.append(meta_dict)

            chunk_counter += 1
    if ids:
        collection.add(
            ids = ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

    print(f"Indexed {len(documents)} documents, {chunk_counter} chunks.")

if __name__ == "__main__":
    SHOPPING_APP_ROOT = "/Users/jacobzhao/Documents/Coding/OnlineShoppingApp"
    ingest_documents(data_dir=SHOPPING_APP_ROOT)





