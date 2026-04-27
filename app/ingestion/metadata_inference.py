from typing import Optional
from pathlib import Path

# ---------- Infer layer / role_scope from path and package ----------

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
