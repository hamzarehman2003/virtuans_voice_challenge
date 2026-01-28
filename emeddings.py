import os
import json
import time
from typing import Any, Dict, List, Optional
import random

from tqdm import tqdm
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ---------------- CONFIG ----------------
CHUNKS_JSONL = "chunks.jsonl"          # your chunk file
CHROMA_PATH = "chroma_db"             # folder where chroma persists data
COLLECTION_NAME = "sunmarke_chunks"

GEMINI_MODEL = "gemini-embedding-001"  # Gemini embedding model
TASK_TYPE = "RETRIEVAL_DOCUMENT"       # best for RAG indexing
BATCH_SIZE = 5                 # was 32
SLEEP_BETWEEN_BATCHES = 8.0    # was 0.2 (robots delay style)
MAX_RETRIES = 10               # was 6
                     # retry on transient errors
# ----------------------------------------

def read_jsonl(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)

def extract_embedding_values(emb: Any) -> List[float]:
    """
    google-genai returns embedding objects; docs show `e.values`. :contentReference[oaicite:3]{index=3}
    This handles both cases: object w/ .values or raw list.
    """
    if hasattr(emb, "values"):
        return list(emb.values)
    return list(emb)

def gemini_embed_texts(client: genai.Client, texts: List[str]) -> List[List[float]]:
    """
    Batch embeddings: Gemini supports passing contents as a list of strings. :contentReference[oaicite:4]{index=4}
    """
    resp = client.models.embed_content(
        model=GEMINI_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(task_type=TASK_TYPE),
    )
    return [extract_embedding_values(e) for e in resp.embeddings]

def with_retries(fn, *, max_retries=10):
    delay = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except Exception as e:
            msg = str(e)
            # If quota/rate-limit: back off harder
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                sleep_s = delay + random.uniform(0, 1.5)
                print(f"Rate-limited (429). Sleeping {sleep_s:.1f}s then retrying...", flush=True)
                time.sleep(sleep_s)
                delay = min(delay * 1.8, 60.0)
                continue

            # Other transient errors: smaller backoff
            if attempt < max_retries:
                sleep_s = 1.0 + random.uniform(0, 1.0)
                print(f"Transient error. Sleeping {sleep_s:.1f}s then retrying...", flush=True)
                time.sleep(sleep_s)
                continue
            raise

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY in your environment first. If you have a .env file, ensure it's in the project root and contains GEMINI_API_KEY=...")
    else:
        # mask key for debug
        print(f"Found GEMINI_API_KEY: {api_key[:6]}... (len={len(api_key)})")

    # Gemini client
    gclient = genai.Client(api_key=api_key)  # official GenAI SDK :contentReference[oaicite:5]{index=5}

    # Chroma persistent DB
    cclient = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = cclient.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # good default for embeddings search
    )

    # Load chunks
    rows: List[Dict[str, Any]] = list(read_jsonl(CHUNKS_JSONL))
    print(f"Loaded {len(rows)} chunks from {CHUNKS_JSONL}")

    # Optional: skip already-ingested IDs (so you can re-run safely)
    # (Chroma doesn't have a fast "exists" check; we do a best-effort get in batches.)
    # We'll just try add; if you want strict dedupe, keep chunk_id stable (you do).

    ids_batch: List[str] = []
    docs_batch: List[str] = []
    metas_batch: List[Dict[str, Any]] = []

    def flush_batch():
        nonlocal ids_batch, docs_batch, metas_batch

        if not ids_batch:
            return

        texts = docs_batch

        embeddings = with_retries(lambda: gemini_embed_texts(gclient, texts))

        # Add to Chroma
        # Note: embeddings are provided explicitly so Chroma won’t try to embed itself.
        collection.add(
            ids=ids_batch,
            documents=docs_batch,
            metadatas=metas_batch,
            embeddings=embeddings,
        )

        ids_batch, docs_batch, metas_batch = [], [], []
        time.sleep(SLEEP_BETWEEN_BATCHES)

    for r in tqdm(rows, desc="Embedding + ingesting"):
        chunk_id = r["chunk_id"]
        text = r["text"]

        # keep metadata small + useful
        meta = {
            "source_file": r.get("source_file"),
            "url": r.get("url"),
            "title": r.get("title"),
            "chunk_index": r.get("chunk_index"),
        }

        ids_batch.append(chunk_id)
        docs_batch.append(text)
        metas_batch.append(meta)

        if len(ids_batch) >= BATCH_SIZE:
            flush_batch()

    flush_batch()

    print("\n✅ Done.")
    print(f"Chroma path: {CHROMA_PATH}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Total items in collection now: {collection.count()}")

    # Quick sanity query
    q = "admissions curriculum wellbeing"
    q_emb = gemini_embed_texts(gclient, [q])[0]
    results = collection.query(query_embeddings=[q_emb], n_results=3)
    print("\nTop 3 results preview:")
    for i, doc in enumerate(results["documents"][0], start=1):
        print(f"\n[{i}] {doc[:300]}...")

if __name__ == "__main__":
    main()
