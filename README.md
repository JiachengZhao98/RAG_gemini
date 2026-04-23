# Gemini RAG V1

## Overview
A minimal RAG system built with Python, Gemini API, and Chroma.

## Features
- Load local .md and .txt files
- Chunk documents
- Generate embeddings with Gemini
- Store vectors in Chroma
- Retrieve top-k chunks
- Answer questions based on retrieved context
- Show sources

## Project Structure
- app/
- data/
- vector_store/
- tests/

## Setup
1. create virtual environment
2. install dependencies
3. add .env
4. run indexer
5. run chat

## Commands
python -m app.smoke_test
python -m app.run_indexer
python -m app.chat

## Limitations
- only supports .md and .txt
- chunking is basic
- no reranking
- no hybrid search
- no memory
