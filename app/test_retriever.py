from app.retriever import retrieve


if __name__ == "__main__":
    query = input("please type your question: ").strip()

    results = retrieve(query, n_results=3)

    if not results:
        print("no result")
    else:
        print("\n=== Retrieval Results ===")
        for i, item in enumerate(results, start=1):
            print(f"\n--- Top {i} ---")
            print(f"id: {item['id']}")
            print(f"distance: {item['distance']}")
            print(f"source: {item['metadata'].get('source')}")
            print(f"filename: {item['metadata'].get('filename')}")
            print("document:")
            print(item["document"])
