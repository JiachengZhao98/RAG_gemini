from pyexpat import model
from app.gemini_client import get_client
from app.config import settings


def test_generatioin():
    client = get_client()
    response = client.models.generate_content(
        model=settings.GEMINI_CHAT_MODEL,
        contents="explain RAG in one sentence"
    )

    print("=== Generation Result ===")
    print(response.text)


def test_embedding():
    client = get_client()

    response = client.models.embed_content(
        model=settings.GEMINI_EMBED_MODEL,
        contents="RAG combines retrieval with generation."
    )

    print("=== Embedding Result ===")
    print(f"Embedding vector count: {len(response.embeddings)}")
    print(f"Embedding dimension: {len(response.embeddings[0].values)}")


if __name__ == "__main__":
    test_generatioin()
    print()
    test_embedding()



