from sentence_transformers import SentenceTransformer # type: ignore

_model = None

def get_embedder():
    global _model
    if _model is None:
        _model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    return _model


def embed_text(text: str) -> list[float]:
    model = get_embedder()
    return model.encode(text, normalize_embeddings=True).tolist()
