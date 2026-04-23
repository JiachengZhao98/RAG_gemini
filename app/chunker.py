from multiprocessing.sharedctypes import Value
def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk size must be > 0")

    if overlap < 0:
        raise ValueError("overlao must be >= 0")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")


    chunks = []
    start = 0
    text_lenth = len(text)

    while (start < text_lenth):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks
