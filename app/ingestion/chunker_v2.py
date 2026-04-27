# app/ingestion/chunker_v2.py
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path
import javalang
import re
from metadata_inference import infer_layer, infer_role_scope

@dataclass
class ChunkMetadata:
    chunk_id: str
    chunk_type: str  # "class_header" | "method" | "file"
    source_path: str
    start_line: int
    end_line: int
    file_type: str
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


# ---------- Annotation parsing helpers ----------

HTTP_MAPPING_ANNOTATIONS = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "PatchMapping": "PATCH",
    "DeleteMapping": "DELETE",
    "RequestMapping": None,  # method field will carry it
}


def annotation_to_str(ann) -> str:
    """Turn a javalang Annotation node into its source-ish form: @Foo or @Foo("x")."""
    name = ann.name
    if ann.element is None:
        return f"@{name}"
    # element may be a list of ElementValuePair or a single Literal
    if hasattr(ann.element, "value"):
        return f'@{name}({ann.element.value})'
    if isinstance(ann.element, list):
        parts = []
        for pair in ann.element:
            if hasattr(pair, "name") and hasattr(pair, "value"):
                parts.append(f"{pair.name}={getattr(pair.value, 'value', pair.value)}")
            else:
                parts.append(str(getattr(pair, "value", pair)))
        return f'@{name}({", ".join(parts)})'
    return f"@{name}"


def extract_mapping_path(ann) -> Optional[str]:
    """From @GetMapping("/foo") or @RequestMapping("/api") pull out the path string."""
    if ann.element is None:
        return ""
    # @GetMapping("/foo") -> element is Literal
    if hasattr(ann.element, "value"):
        return ann.element.value.strip('"')
    # @GetMapping(value = "/foo") -> element is list of ElementValuePair
    if isinstance(ann.element, list):
        for pair in ann.element:
            if getattr(pair, "name", None) in (None, "value", "path"):
                v = getattr(pair, "value", None)
                if v is not None and hasattr(v, "value"):
                    return v.value.strip('"')
    return None


def get_http_mapping(annotations) -> tuple[Optional[str], Optional[str]]:
    """Return (http_method, path) for a method's mapping annotation."""
    for ann in annotations:
        if ann.name in HTTP_MAPPING_ANNOTATIONS:
            method = HTTP_MAPPING_ANNOTATIONS[ann.name]
            path = extract_mapping_path(ann) or ""
            return method, path
    return None, None


# ---------- Line-number resolution (javalang only gives token positions, need to scan source) ----------

def find_method_lines(source_lines: list[str], method_node) -> tuple[int, int]:
    """Approximate start/end line for a method node.
    javalang gives position.line for the method declaration line.
    End line needs brace matching on the source."""
    start = method_node.position.line if method_node.position else 1
    # Absorb annotation lines sitting above the method
    i = start - 2  # 0-indexed, start is 1-indexed
    while i >= 0 and source_lines[i].strip().startswith("@"):
        start -= 1
        i -= 1
    # Walk down with brace balancing to find the end
    depth = 0
    seen_brace = False
    end = start
    for line_no in range(start - 1, len(source_lines)):
        line = source_lines[line_no]
        for ch in line:
            if ch == "{":
                depth += 1
                seen_brace = True
            elif ch == "}":
                depth -= 1
                if seen_brace and depth == 0:
                    return start, line_no + 1
        end = line_no + 1
    return start, end


# ---------- Main chunking entry point ----------

def chunk_java_file(content: str, relative_path: str) -> list[Chunk]:
    try:
        tree = javalang.parse.parse(content)
    except javalang.parser.JavaSyntaxError as e:
        # V1: on parse failure, fall back to one chunk for the whole file
        return [_file_fallback_chunk(content, relative_path, "java")]

    source_lines = content.splitlines()
    package = tree.package.name if tree.package else None
    layer = infer_layer(package or "", relative_path)
    role_scope = infer_role_scope(package or "", relative_path)

    chunks = []
    for path, class_node in tree.filter(javalang.tree.ClassDeclaration):
        chunks.extend(_chunk_class(
            class_node=class_node,
            source_lines=source_lines,
            relative_path=relative_path,
            package=package,
            layer=layer,
            role_scope=role_scope,
        ))
    return chunks


def _chunk_class(class_node, source_lines, relative_path, package, layer, role_scope) -> list[Chunk]:
    class_name = class_node.name
    class_annotations = [annotation_to_str(a) for a in (class_node.annotations or [])]

    # Extract base_path from @RequestMapping
    base_path = None
    for ann in (class_node.annotations or []):
        if ann.name == "RequestMapping":
            base_path = extract_mapping_path(ann) or ""

    # Field-injected dependencies
    injected = []
    for field_decl in (class_node.fields or []):
        has_autowired = any(a.name == "Autowired" for a in (field_decl.annotations or []))
        is_final = "final" in (field_decl.modifiers or set())
        if has_autowired or is_final:
            for d in field_decl.declarators:
                # field_decl.type.name is the type name
                type_name = getattr(field_decl.type, "name", None)
                if type_name:
                    injected.append(type_name)

    chunks = []
    # --- class header chunk ---
    chunks.append(_make_class_header_chunk(
        class_node, source_lines, relative_path, package, class_name,
        class_annotations, base_path, injected, layer, role_scope,
    ))

    # --- method chunks ---
    for method in (class_node.methods or []):
        chunks.append(_make_method_chunk(
            method, source_lines, relative_path, package, class_name,
            base_path, layer, role_scope,
        ))

    return chunks


def _make_class_header_chunk(class_node, source_lines, relative_path, package,
                             class_name, class_annotations, base_path,
                             injected, layer, role_scope) -> Chunk:
    # Synthesized content
    lines = [
        f"Class: {class_name}",
        f"Package: {package or '(default)'}",
    ]
    if layer:
        lines.append(f"Layer: {layer}" + (f" ({role_scope})" if role_scope else ""))
    if base_path:
        lines.append(f"Base path: {base_path}")
    if class_annotations:
        lines.append(f"Annotations: {', '.join(class_annotations)}")
    if injected:
        lines.append(f"Dependencies: {', '.join(injected)}")
    if class_node.methods:
        lines.append("Methods:")
        for m in class_node.methods:
            sig = _method_signature(m, base_path)
            lines.append(f"  - {sig}")

    content = "\n".join(lines)
    start_line = class_node.position.line if class_node.position else 1
    end_line = start_line  # synthetic chunk, not tied to end; or use last method's end

    meta = ChunkMetadata(
        chunk_id=f"{class_name}__class__L{start_line}",
        chunk_type="class_header",
        source_path=relative_path,
        start_line=start_line,
        end_line=len(source_lines),
        file_type="java",
        package=package,
        class_name=class_name,
        fq_name=f"{package}.{class_name}" if package else class_name,
        layer=layer,
        role_scope=role_scope,
        annotations=class_annotations,
        injected_dependencies=injected,
        endpoint_path=base_path,
        is_synthetic=True,
    )
    return Chunk(content=content, metadata=meta)


def _make_method_chunk(method, source_lines, relative_path, package, class_name,
                       base_path, layer, role_scope) -> Chunk:
    start, end = find_method_lines(source_lines, method)
    method_source = "\n".join(source_lines[start - 1:end])

    annotations = [annotation_to_str(a) for a in (method.annotations or [])]
    http_method, method_path = get_http_mapping(method.annotations or [])

    # Build full endpoint_path
    endpoint_path = None
    if http_method is not None:
        base = (base_path or "").rstrip("/")
        sub = (method_path or "").strip()
        if sub and not sub.startswith("/"):
            sub = "/" + sub
        endpoint_path = (base + sub).rstrip("/") or "/"

    # Extract @PathVariable / @RequestParam
    path_params, query_params = [], []
    for p in (method.parameters or []):
        for ann in (p.annotations or []):
            if ann.name == "PathVariable":
                path_params.append(p.name)
            elif ann.name == "RequestParam":
                query_params.append(p.name)

    # Plan-B prefix
    prefix_bits = [f"In class: {class_name}"]
    if layer or role_scope:
        lr = "/".join(x for x in [layer, role_scope] if x)
        prefix_bits[0] += f" ({lr}"
        if base_path:
            prefix_bits[0] += f", base path {base_path}"
        prefix_bits[0] += ")"
    elif base_path:
        prefix_bits[0] += f" (base path {base_path})"
    prefix = f"// {prefix_bits[0]}"
    content = f"{prefix}\n{method_source}"

    meta = ChunkMetadata(
        chunk_id=f"{class_name}_{method.name}_L{start}",
        chunk_type="method",
        source_path=relative_path,
        start_line=start,
        end_line=end,
        file_type="java",
        package=package,
        class_name=class_name,
        method_name=method.name,
        fq_name=f"{package}.{class_name}#{method.name}" if package else f"{class_name}#{method.name}",
        layer=layer,
        role_scope=role_scope,
        http_method=http_method,
        endpoint_path=endpoint_path,
        path_params=path_params,
        query_params=query_params,
        annotations=annotations,
    )
    return Chunk(content=content, metadata=meta)


def _method_signature(method, base_path: Optional[str]) -> str:
    params = ", ".join(f"{getattr(p.type, 'name', '?')} {p.name}" for p in (method.parameters or []))
    ret = getattr(method.return_type, "name", "void") if method.return_type else "void"
    http_method, path = get_http_mapping(method.annotations or [])
    if http_method:
        full = ((base_path or "").rstrip("/") + ("/" + path if path and not path.startswith("/") else path or "")).rstrip("/") or "/"
        return f"{http_method:<6} {full:<40} → {method.name}({params}): {ret}"
    return f"{method.name}({params}): {ret}"


def _file_fallback_chunk(content, relative_path, file_type):
    lines = content.splitlines()
    return Chunk(
        content=content,
        metadata=ChunkMetadata(
            chunk_id=f"{Path(relative_path).name}__file",
            chunk_type="file",
            source_path=relative_path,
            start_line=1,
            end_line=len(lines),
            file_type=file_type,
        ),
    )
