#!/usr/bin/env python3
"""
Seed the Pinecone vector index with JUST CS department knowledge.

Usage (run from the backend/ directory):
    python scripts/seed_knowledge_base.py

Requirements:
    - GEMINI_API_KEY must be set (used for text-embedding-004 / gemini-embedding-001)
    - PINECONE_API_KEY must be set
    - PINECONE_INDEX_NAME must be set (default: just-cs-advisor)
    - The Pinecone index must already exist with dimension=768
"""

import os
import sys
import time
import hashlib
from pathlib import Path
from typing import Iterator

# Allow running from the scripts/ folder or the backend/ folder
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")

CHUNK_SIZE = 800  # characters per chunk
CHUNK_OVERLAP = 150  # character overlap between consecutive chunks
BATCH_SIZE = 50  # vectors per upsert batch


def _chunks(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> Iterator[str]:
    """Yield text chunks with overlap."""
    start = 0
    while start < len(text):
        end = start + size
        yield text[start:end].strip()
        start += size - overlap


def _chunk_id(filename: str, index: int) -> str:
    raw = f"{filename}::{index}"
    return hashlib.md5(raw.encode()).hexdigest()


def load_documents() -> list[dict]:
    """Load all .txt files from the knowledge_base directory."""
    kb_dir = BASE_DIR / "knowledge_base"
    docs = []
    for txt_file in sorted(kb_dir.glob("*.txt")):
        print(f"  Loading: {txt_file.name}")
        content = txt_file.read_text(encoding="utf-8")
        for i, chunk in enumerate(_chunks(content)):
            if len(chunk) < 50:
                continue  # skip very short fragments
            docs.append({
                "id": _chunk_id(txt_file.stem, i),
                "text": chunk,
                "source_file": txt_file.name,
                "chunk_index": i,
            })
    print(f"  Total chunks: {len(docs)}")
    return docs


def embed_documents(docs: list[dict], client) -> list[dict]:
    """Add embeddings to each document chunk using the official Google GenAI SDK."""
    from google.genai import types

    texts = [d["text"] for d in docs]
    print(f"  Embedding {len(texts)} chunks via gemini-embedding-001 (768-dim)...")

    batch_size = 20
    all_vectors = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i: i + batch_size]
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=batch,
            config=types.EmbedContentConfig(output_dimensionality=768),
        )
        vecs = [embedding.values for embedding in response.embeddings]
        all_vectors.extend(vecs)
        print(f"    Embedded {min(i + batch_size, len(texts))}/{len(texts)}")
        time.sleep(0.5)

    for doc, vec in zip(docs, all_vectors):
        doc["vector"] = vec
    return docs


def upsert_to_pinecone(index, docs: list[dict]) -> None:
    """Upsert all document vectors to Pinecone in batches."""
    print(f"  Upserting {len(docs)} vectors to Pinecone...")
    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i: i + BATCH_SIZE]
        vectors = [
            {
                "id": d["id"],
                "values": d["vector"],
                "metadata": {
                    "text": d["text"],
                    "source_file": d["source_file"],
                    "chunk_index": d["chunk_index"],
                },
            }
            for d in batch
        ]
        index.upsert(vectors=vectors)
        print(f"    Upserted {min(i + BATCH_SIZE, len(docs))}/{len(docs)}")
        time.sleep(0.2)


def main() -> None:
    print("=" * 60)
    print("  JUST CS Advisor — Pinecone Knowledge Base Seeder")
    print("=" * 60)

    # Validate environment
    gemini_key = os.getenv("GEMINI_API_KEY")
    pinecone_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME", "just-cs-advisor")

    if not gemini_key:
        print("ERROR: GEMINI_API_KEY is not set in .env")
        sys.exit(1)
    if not pinecone_key:
        print("ERROR: PINECONE_API_KEY is not set in .env")
        sys.exit(1)

    print(f"\nPinecone index : {index_name}")
    print(f"Knowledge base : {BASE_DIR / 'knowledge_base'}\n")

    # 1. Load and chunk documents
    print("[1/4] Loading knowledge base documents...")
    docs = load_documents()
    if not docs:
        print("ERROR: No documents found in knowledge_base/. Add .txt files first.")
        sys.exit(1)

    # 2. Initialise embeddings (Official Google GenAI Client)
    print("\n[2/4] Initialising embedding model...")
    from google import genai
    client = genai.Client(api_key=gemini_key)


    # 3. Embed documents
    print("\n[3/4] Generating embeddings...")
    docs = embed_documents(docs, client)

    # 4. Upsert to Pinecone
    print("\n[4/4] Upserting to Pinecone...")
    from pinecone._client import Pinecone  # v9 lazy-exports via __init__.__getattr__
    pc = Pinecone(api_key=pinecone_key)
    index = pc.Index(index_name)
    upsert_to_pinecone(index, docs)

    # Summary
    stats = index.describe_index_stats()
    print(f"\n{'=' * 60}")
    print(f"  Seeding complete!")
    print(f"  Total vectors in index: {stats.total_vector_count}")
    print(f"{'=' * 60}")
    print("\nNext step: restart your FastAPI server and test the chatbot.")


if __name__ == "__main__":
    main()