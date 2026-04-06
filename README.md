# Local RAG Q&A System

A fully local Retrieval-Augmented Generation (RAG) system — no API dependency.

## Overview

This project implements a complete RAG pipeline running entirely on local hardware:
- Documents are encoded into vectors using Sentence-Transformers
- Vectors are indexed and stored with Chroma for fast similarity search
- Retrieved context is passed to a local Qwen2 LLM to generate answers
- Interactive query loop for real-time Q&A

## Architecture
```
User Query
    ↓
Sentence-Transformers (local embedding)
    ↓
Chroma Flat Index (brute-force similarity search → top-3 docs)
    ↓
Prompt Assembly (context + query)
    ↓
Qwen2-0.5B-Instruct (local LLM, fully offline)
    ↓
Answer
```

## Tech Stack

- **Embeddings**: Sentence-Transformers (local, CPU)
- **Vector DB**: Chroma (default Flat index)
- **LLM**: Qwen2-0.5B-Instruct (local, fully offline)

## Quick Start
```bash
rag_env\Scripts\activate
(rag_env) 你的文件路径
```

## Key Features

- 100% local execution — no data leaves your machine
- Swappable document corpus — edit the `documents` list
- Swappable LLM — replace Qwen2 with any HuggingFace model
- Interactive CLI for real-time querying
-
## Markdown
RAG:
<img width="2306" height="344" alt="image" src="https://github.com/user-attachments/assets/b4d18cb3-bbee-459c-942e-a9adfceb5380" />
py:
<img width="1118" height="748" alt="image" src="https://github.com/user-attachments/assets/3164587f-1d86-4804-9715-0f85b751c28c" />

