import chromadb
from app.config import settings
from app.gemini_client import get_client
from app.loader import load_text_files
from app.chunker import chunk_text

COLLECTION_NAME = "rag_docs"


def get_chroma_collection():
    chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
    collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
    return collection


def embed_text(text: str) -> list[float]:
    client = get_client()
    response = client.models.embed_content(
        model=settings.GEMINI_EMBED_MODEL,
        contents=text
    )
    return response.embeddings[0].values

"""
index_documents: index documents from a directory

Args:
    data_dir (str, optional): directory containing text files. Defaults to "data".

Returns:
    None
"""
def index_documents(data_dir: str = "data"):
    documents = load_text_files(data_dir)
    collection = get_chroma_collection()

    ids = []
    embeddings = []
    metadatas = []
    texts = []

    chunk_counter = 0

    for doc in documents:
        chunks = chunk_text(doc["text"], chunk_size=300, overlap=50)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc['filename']}_chunk_{i}"
            embedding = embed_text(chunk)

            ids.append(chunk_id)
            embeddings.append(embedding)
            texts.append(chunk)
            metadatas.append({
                "source": doc["source"],
                "filename": doc["filename"],
                "chunk_index": i
            })

            chunk_counter += 1
    if ids:
        collection.add(
            ids = ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

    print(f"Indexed {len(documents)} documents, {chunk_counter} chunks.")





