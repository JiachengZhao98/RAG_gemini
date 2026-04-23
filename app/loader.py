from pathlib import Path
"""
load_text_files: load text files from a directory 

Args:
    data_dir (str): directory containing text files

Returns:
    list[str]: list of text files with metadata (source, filename)
"""
def load_text_files(data_dir: str) -> list[str]:
    documents = []
    base_path = Path(data_dir)

    for file_path in base_path.rglob("*"):
        if file_path.suffix.lower() not in [".md", ".txt", ".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".json"]:
            continue

        text = file_path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        documents.append({
            "text": text,
            "source": str(file_path),
            "filename": file_path.name,
        })

    return documents

