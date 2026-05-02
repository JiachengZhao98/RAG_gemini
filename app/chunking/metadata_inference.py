from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field, asdict

# ---------- Infer layer / role_scope from path and package ----------

@dataclass
class ChunkMetadata:
    chunk_id: str
    chunk_type: str  # "class_header" | "method" | "file" | "char_window"
    source_path: str
    start_line: int
    end_line: int
    file_type: str
    chunker_version: str
    package: Optional[str] = None
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    fq_name: Optional[str] = None
    layer: Optional[str] = None
    role_scope: Optional[str] = None
    http_method: Optional[str] = None
    endpoint_path: Optional[str] = None
    path_params: list = field(default_factory=list)
    query_params: list = field(default_factory=list)
    annotations: list = field(default_factory=list)
    calls: list = field(default_factory=list)
    injected_dependencies: list = field(default_factory=list)
    is_synthetic: bool = False


@dataclass
class Chunk:
    content: str
    metadata: ChunkMetadata

    def to_dict(self):
        return {"content": self.content, "metadata": asdict(self.metadata)}

LAYER_KEYWORDS = {
    "controller": "controller",
    "service": "service",
    "dao": "dao",
    "repository": "dao",
    "dto": "dto",
    "entity": "entity",
    "model": "entity",
    "config": "config",
    "aspect": "aspect",
    "security": "config",
}

ROLE_KEYWORDS = {"buyer", "seller", "auth"}

def infer_layer(package: str, relative_path: str) -> Optional[str]:
    parts = (package or "").lower().split(".") + relative_path.lower().replace("\\", "/").split("/")
    for p in parts:
        if p in LAYER_KEYWORDS:
            return LAYER_KEYWORDS[p]
    return None


def infer_role_scope(package: str, relative_path: str) -> Optional[str]:
    parts = (package or "").lower().split(".") + relative_path.lower().replace("\\", "/").split("/")
    for p in parts:
        if p in ROLE_KEYWORDS:
            return p
    return None

def infer_class_name_from_path(relative_path: str) -> Optional[str]:
    if (not relative_path.endswith(".java")):
        return None
    path = Path(relative_path)
    return path.stem
