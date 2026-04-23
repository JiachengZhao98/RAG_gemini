def build_rag_prompt(question: str, retrieved_docs: list[dict]) -> str:
    if not retrieved_docs:
        return f""" You are a helpful assistant.
                    The user asked:
                    {question}
                    No relevant context was retrieved. You can ONLY answer you do not know.
                """

    context_blocks = []
    for idx, item in enumerate(retrieved_docs, start=1):
        metadata=item["metadata"]
        source=metadata.get("source", "unknown")
        filename=metadata.get("filename", "unknown")
        document=item["document"]

        context_blocks.append(
            f"""[Context {idx}]
                Source: {source}
                Filename: {filename}
                Content: {document}
            """
        )

        context_text = "\n\n".join(context_blocks)
        prompt = f"""You are a helpful RAG assistant.
                    Answer the user's question ONLY based on the retrieved context below.
                    If the answer is not contained in the context, ONLY say you do not know.
                    Do not make up facts.
                    Be concise and accurate.

                    User Question:
                    {question}

                    Retrieved Context:
                    {context_text}
                    Now provide the answer.
                """
    return prompt
