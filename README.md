# Local RAG Q&A System

A fully local Retrieval-Augmented Generation (RAG) system — no cloud API, no OpenAI dependency.

## Overview

This project implements a complete RAG pipeline running entirely on local hardware:
- Documents are encoded into vectors using Sentence-Transformers
- Vectors are indexed with FAISS for fast similarity search
- Retrieved context is passed to a local Qwen2 LLM to generate answers
- Interactive query loop for real-time Q&A

## Architecture
```
User Query
    ↓
Sentence-Transformers (local embedding)
    ↓
FAISS IndexFlatL2 (similarity search → top-3 docs)
    ↓
Prompt Assembly (context + query)
    ↓
Qwen2-0.5B-Instruct (local LLM, fully offline)
    ↓
Answer
```

## Tech Stack

- **Embeddings**: Sentence-Transformers (local, CPU)
- **Vector Index**: FAISS (IndexFlatL2)
- **LLM**: Qwen2-0.5B-Instruct (local, via HuggingFace)
- **No external API required** — runs fully offline

## Quick Start
```bash
pip install faiss-cpu sentence-transformers transformers torch
python faiss_demo.py
```

## Key Features

- 100% local execution — no data leaves your machine
- Swappable document corpus — edit the `documents` list
- Swappable LLM — replace Qwen2 with any HuggingFace model
- Interactive CLI for real-time querying
