from pathlib import Path
from chunker import chunk_text as v1_chunk
from chunker_v2 import chunk_java_file as v2_chunk

SHOPPING_APP_ROOT = Path("/Users/jacobzhao/Documents/Coding/OnlineShoppingApp")
java_file = SHOPPING_APP_ROOT / "src/main/java/com/superdupermart/shoppingapp/controller/buyer/OrderController.java"

src = java_file.read_text()
rel = str(java_file.relative_to(SHOPPING_APP_ROOT))

v1_chunks = v1_chunk(src, rel)
v2_chunks = v2_chunk(src, rel)

print(f"V1 chunks: {len(v1_chunks)}")
print(f"V2 chunks: {len(v2_chunks)}")
print()

# Both should agree on file-level fields
print("=== V1 first chunk file-level metadata ===")
m1 = v1_chunks[0].metadata
print(f"  layer:       {m1.layer}")
print(f"  role_scope:  {m1.role_scope}")
print(f"  class_name:  {m1.class_name}")
print(f"  file_type:   {m1.file_type}")
print()

print("=== V2 first chunk file-level metadata ===")
m2 = v2_chunks[0].metadata
print(f"  layer:       {m2.layer}")
print(f"  role_scope:  {m2.role_scope}")
print(f"  class_name:  {m2.class_name}")
print(f"  file_type:   {m2.file_type}")
print()

# Assert they match
assert m1.layer == m2.layer, "layer mismatch!"
assert m1.role_scope == m2.role_scope, "role_scope mismatch!"
assert m1.class_name == m2.class_name, "class_name mismatch!"
print("V1 and V2 file-level metadata match!")
print()

# V2 should additionally have method-level fields
print("=== V2 chunk types ===")
for c in v2_chunks:
    print(f"  {c.metadata.chunk_type:15} {c.metadata.method_name or '(no method)':20} "
          f"{c.metadata.http_method or '':5} {c.metadata.endpoint_path or ''}")
