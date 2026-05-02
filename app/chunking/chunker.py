from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from .metadata_inference import infer_layer, infer_role_scope, infer_class_name_from_path, Chunk, ChunkMetadata

CHUNKER_VERSION = "v1"

def chunk_text(content: str, relative_path: str, chunk_size: int = 300, overlap: int = 50) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk size must be > 0")

    if overlap < 0:
        raise ValueError("overlap must be >= 0")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")


    layer = infer_layer("", relative_path)
    role_scope = infer_role_scope("", relative_path)

    chunks = []
    start = 0
    text_length = len(content)
    idx = 0

    while (start < text_length):
        end = start + chunk_size
        chunk = content[start:end].strip()
        if chunk:
            chunks.append(Chunk(
                content=chunk,
                metadata=ChunkMetadata(
                    chunker_version=CHUNKER_VERSION,
                    layer=layer,
                    role_scope=role_scope,
                    source_path=relative_path,
                    chunk_id=f"{relative_path}__chunk_{idx}",
                    chunk_type="char_window",
                    class_name=infer_class_name_from_path(relative_path),
                    start_line=content[:start].count("\n") + 1,
                    end_line=content[:end].count("\n") + 1,
                    file_type=Path(relative_path).suffix.lstrip(".").lower() # get the file type from the file suffix, e.g. "PlaceOrder.java" is a java file
        )))
        start += chunk_size - overlap
        idx += 1

    return chunks
