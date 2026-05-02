from app.ingest import get_chroma_collection, embed_text

"""
retrieve: retrieve documents from chroma collection

Args:
    query (str): query string
    n_results (int, optional): number of results to retrieve. Defaults to 3.

Returns:
    list[dict]: list of retrieved documents
"""

def retrieve(query: str, n_results: int = 3) -> list[dict]:
    collection = get_chroma_collection()
    query_embedding = embed_text(query)

    result = collection.query(
        # query_embeddings: the embedding of the query
        query_embeddings=[query_embedding],
        # n_results: the number of results to retrieve
        n_results=n_results,
        # documents: the text content of the documents
        # metadatas: the metadata of the documents
        # distances: the distance between the query and the documents
        include=["documents", "metadatas", "distances"]
    )

    ids = result["ids"][0]
    documents = result["documents"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    hits = []
    DISTANCE_THRESHOLD = 1.0

    for doc_id, document, metadata, distance in zip(
        ids, documents, metadatas, distances
    ):
        # if distance > DISTANCE_THRESHOLD:
        #     continue

        hits.append(
            {
                "id": doc_id,
                "document": document,
                "metadata": metadata,
                "distance": distance,
            }
        )
    return hits
