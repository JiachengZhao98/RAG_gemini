# Step 0: V1 vs V2 Chunker Baseline

## Setup
- **Corpus**: OnlineShoppingApp (63 files — Java sources + README + properties + pom)
- **V1 chunker**: fixed-size character window — 300 chars, 50-char overlap, no syntax awareness. Layer / role_scope / class_name inferred from path only.
- **V2 chunker**: javalang AST-driven for `.java` files. Emits one synthesized `class_header` chunk per class (package, base path, injected deps, method signatures) plus one `method` chunk per method. Method chunks carry `http_method`, resolved `endpoint_path` (class `@RequestMapping` + method mapping), `path_params`, `query_params`, `annotations`, `fq_name`. Non-Java files fall back to V1.
- **Shared**: `metadata_inference` module — same `layer` / `role_scope` rules across both versions, so chunking strategy is the only independent variable.
- **Embedding**: `BAAI/bge-small-en-v1.5`, normalized.
- **Vector store**: Chroma, separate collections (`rag_v1`, `rag_v2`).

## Stats
- V1: 382 chunks (all `char_window`)
- V2: 297 chunks — 208 `method` + 46 `class_header` + 43 `char_window` fallback (non-Java)
- 29 method chunks with non-empty `endpoint_path` (matches 8 controllers × ~3.6 endpoints)
- **V2 has 22% fewer chunks than V1, with semantically meaningful boundaries — fewer but better.**

## Queries tested (5)
1. *how does JWT authentication work*
2. *where is the place order endpoint*
3. *watchlist duplicate prevention*
4. *how does the seller view top profit products*
5. *what is the global exception handler*

## Findings
1. **V2 wins on chunk completeness.** V1 ranked README and the service implementation ahead of the controller method. V2 ranked the controller method at #2 — README still dominated due to natural-language match — but the V2 chunk now contained the complete method with endpoint metadata, while V1's chunk was a half-broken fragment starting mid-parameter list.
> Concrete example — query "where is the place order endpoint":
>
> **V1 top-3** (BGE distances 0.40, 0.53, 0.55):
> 1. README.md char-window: `"...POST /api/orders / Place an order..."`
> 2. OrderServiceImpl: `"...placeOrder(orderRequest)..."` (service, not endpoint)
> 3. OrderController fragment: `"RequestBody OrderRequestDto orderRequest) { orderService.placeOrder..."` (mid-method)
>
> **V2 top-3** (distances 0.40, 0.48, 0.56):
> 1. README.md char-window (same)
> 2. OrderController.placeOrder method chunk — full method body, prefix `// In class: OrderController (controller/buyer, base path /api/buyer/orders)`, metadata `http_method=POST, endpoint_path=/api/buyer/orders`
> 3. OrderController class_header — full endpoint listing
2. **V2 metadata is passive in dense-only retrieval.** `endpoint_path`, `http_method`, `layer` are populated but never read by the retriever — they ride along in Chroma and could only help if a reranker or BM25 pass consumed them. **Motivates BM25 hybrid + metadata reranking in W2.**
3. **README dominates endpoint queries.** Even with V2, README mentions of "place order" embed close to the natural-language query. **Motivates source-type weighting** (penalize `.md` for code-locating intents).
4. **Layer-intent mismatch persists.** Queries about *behavior* ("how does …") still surface DAOs and DTOs because BGE doesn't know that "how does X work" implies a service-layer answer. Metadata is there (`layer=service`); retrieval just doesn't use it. **Motivates intent → layer reranking.**
5. **`class_header` relevance unclear.** Synthetic summary content (structured lists like Methods: \n - GET /api/foo → bar()) is out-of-distribution for BGE's training corpus — sentence pairs of natural text. Method bodies, while code, are closer to programming text BGE has seen during training. Whether class_header chunks earn their slot is untested.

## Limitations carried into V2
- **Abstract / interface methods**: `find_method_lines` brace-matches on source — interface declarations with no body would fail silently. Not hit in this corpus (all DAOs are concrete) but a known fragility.
- **Inner-class methods**: `tree.filter(ClassDeclaration)` walks all classes, but methods are only attributed to their immediate enclosing class via `class_node.methods`; static helpers inside DTOs may be miscounted or duplicated.
- **Non-Java files** fall back to V1 char-window — properties, pom.xml, and README share V1's annotation-splitting weakness.
- **`calls` metadata slot is empty.** Reserved in `ChunkMetadata` for V3 graph retrieval; not extracted yet.
- **Short DTO getters add noise.** ~30–40 method chunks are 3-line getters / setters with little semantic content; they pad recall at no precision benefit.

## What this baseline unlocks
With V2 in place, chunking is no longer the dominant bottleneck — the next gains come from **using** the metadata V2 produces. W2 plan: BM25 hybrid over `endpoint_path` + `fq_name`, then a metadata-aware reranker keyed off query intent (endpoint locator vs. behavior question vs. config lookup).

## Reproducibility

```bash
# Setup
git clone <your-repo>
cd RAG
pip install -r requirements.txt

# Point to corpus
export SHOPPING_APP_ROOT=/path/to/OnlineShoppingApp

# Ingest both versions
CHUNKER_VERSION=v1 python -m app.ingest
CHUNKER_VERSION=v2 python -m app.ingest

# Manual retrieval comparison
CHUNKER_VERSION=v1 python -m scripts.manual_retrieval > results_v1.txt
CHUNKER_VERSION=v2 python -m scripts.manual_retrieval > results_v2.txt
diff results_v1.txt results_v2.txt
```

Outputs:
- Chroma collections: `./chroma_db/rag_v1`, `./chroma_db/rag_v2`
- Embedding model: `BAAI/bge-small-en-v1.5` (auto-downloaded ~130MB on first run)
