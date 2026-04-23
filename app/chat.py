from app.gemini_client import get_client
from app.config import settings
from app.retriever import retrieve
from app.prompt import build_rag_prompt

def answer_question(question: str, n_results: int=3) -> dict:
    retrieved_docs = retrieve(question, n_results=n_results)
    prompt = build_rag_prompt(question, retrieved_docs)

    client = get_client()
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_CHAT_MODEL,
            contents=prompt
        )
        answer_text = response.text
    except ClientError as e:
        answer_text = f"Gemini API error: {e}"

    unique_sources = []
    seen = set()

    for item in retrieved_docs:
        metadata = item["metadata"]
        source = metadata.get("source", "unknown")
        filename = metadata.get("filename", "unknown")
        key = (source, filename)


        if key not in seen:
            seen.add(key)
            unique_sources.append({
                "source": source,
                "filename": filename
            })

    return {
        "answer": response.text,
        "sources": unique_sources,
        "retrieved_docs": retrieved_docs
    }


def main():
    while True:
        question = input("please type your question (or 'exit'): ").strip()
        if question.lower() in ["exit", "quit"]:
            print("bye")
            break

        if not question:
            print("question can not be empty!")
            continue

        result = answer_question(question, n_results=3)
        print("\n=== Answer ===")
        print(result["answer"])

        print("\n=== Sources ===")
        if "do not know" in result["answer"].lower():
            print("No sources found.")
        else:
            for i, item in enumerate(result["sources"], start=1):
                print(f"{i}. {item['filename']} ({item['source']})")

if __name__ == "__main__":
    main()


