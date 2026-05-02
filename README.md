# RAG

## Overview
A RAG system built with Python, the Gemini API, and Chroma. Supports two chunking strategies — a simple text chunker (V1) and an AST-aware Java chunker (V2) that emits structured metadata (layer, role/scope, HTTP method+path, injected dependencies, annotations).

## Features
- Walks a source tree and loads files (excludes build artifacts, binaries, etc.)
- Two chunkers, switchable via `CHUNKER_VERSION`:
  - **V1** — fixed-size character-window chunker (300 chars, 50 overlap), no syntax awareness. Used as baseline for evaluation comparison.
  - **V2** — `javalang` AST-based chunking for `.java`, with inferred metadata; falls back to V1 for non-Java files
- Embeds chunks with `BAAI/bge-small-en-v1.5` (local, no API costs — ingest can be re-run dozens of times during evaluation iteration)
- Stores vectors in Chroma (one collection per chunker version: `rag_v1`, `rag_v2`)
- Retrieves top-k chunks
- Answers questions over the retrieved context, with source attribution

## Experiments & Results

- [Step 0: V1 vs V2 Chunker Baseline](experiments/step0/README.md) —
  Controlled comparison setup, 5-query manual retrieval, V1 vs V2
  findings, and motivations for upcoming work.

(More to come: W1 evaluation framework, W2 BM25 hybrid + reranker,
W5 chunking ablation.)

## Corpus

The default corpus for evaluation is a Spring Boot reference project
([OnlineShoppingApp](https://github.com/JiachengZhao98/Online_Shopping_App)),
chosen because it has:

- Clear architectural layers (controller / service / dao / entity / dto)
- Real Spring DI, JPA, Spring Security, and AOP — exposes the rich
  metadata V2 chunker is designed to extract
- ~50 Java files, enough for meaningful chunking and retrieval
  comparison without slow ingest

Configure the corpus path via `SHOPPING_APP_ROOT` (or edit
`app/ingest.py`'s `__main__` block).

## Project Structure
- [app/](app/) — main package
  - [app/ingest.py](app/ingest.py) — file walking + ingestion pipeline
  - [app/chunking/chunker.py](app/chunking/chunker.py) — V1 text chunker
  - [app/chunking/chunker_v2.py](app/chunking/chunker_v2.py) — V2 Java AST chunker
  - [app/chunking/metadata_inference.py](app/chunking/metadata_inference.py) — layer / role-scope inference + shared `Chunk` / `ChunkMetadata` schema
  - [app/embedder.py](app/embedder.py) — Embeds chunks with `BAAI/bge-small-en-v1.5`
  - [app/retriever.py](app/retriever.py) — Chroma top-k retrieval
  - [app/prompt.py](app/prompt.py) — RAG prompt builder
  - [app/chat.py](app/chat.py) — interactive Q&A loop
  - [app/config.py](app/config.py) — env-backed settings
- [data/](data/) — local sample documents
- [vector_store/](vector_store/) — persisted Chroma DB
- [scripts/](scripts/) — ad-hoc scripts (e.g. manual retrieval)
- [experiments/](experiments/) — chunking / retrieval experiments
- [tests/](tests/) — evaluation questions

## Setup
1. Create a virtual environment and activate it.
2. `pip install -r requirements.txt`
3. Create `.env` with:
   ```
   GOOGLE_API_KEY=...
   GEMINI_CHAT_MODEL=gemini-...
   GEMINI_EMBED_MODEL=gemini-embedding-...
   CHROMA_DIR=./vector_store
   ```
4. Run the indexer, then chat.

## Commands
```bash
python -m app.smoke_test              # sanity check
python -m app.ingest                  # build / rebuild the index
python -m app.chat                    # ask questions
CHUNKER_VERSION=v2 python -m app.ingest   # ingest with the V2 Java chunker
```

Re-running ingestion drops and recreates the collection for the active `CHUNKER_VERSION`.

## V2 metadata fields
## V2 metadata fields

`ChunkMetadata` (see [metadata_inference.py](app/chunking/metadata_inference.py))
carries:

- **Identity**: `chunk_id`, `chunk_type` (class_header / method / char_window),
  `chunker_version`, `fq_name`
- **Location**: `source_path`, `start_line`, `end_line`, `file_type`
- **Code semantics**: `package`, `class_name`, `method_name`,
  `layer` (controller / service / dao / dto / entity / config / aspect),
  `role_scope` (buyer / seller / auth)
- **HTTP semantics** (controller methods only): `http_method`,
  `endpoint_path`, `path_params`, `query_params`
- **Annotations & dependencies**: `annotations`, `calls`,
  `injected_dependencies`

List-valued fields are flattened to comma-separated strings on Chroma write (Chroma metadata only supports scalar values).

## Limitations
- V2 AST parsing is Java-only; other file types fall back to V1
- Heuristic layer / role-scope inference (package- and path-based)
- No reranking
- No hybrid (BM25 + vector) search
- No conversational memory
