from typing import Any, List, Tuple

from google.genai import types

from . import config


def _embedding_values(e: Any) -> List[float]:
    return list(e.values) if hasattr(e, "values") else list(e)


def embed_query(genai_client, text: str) -> List[float]:
    # Embed a query for vector search.
    resp = genai_client.models.embed_content(
        model=config.EMBED_MODEL,
        contents=[text],
        config=types.EmbedContentConfig(task_type=config.EMBED_TASK_TYPE),
    )
    return _embedding_values(resp.embeddings[0])


def retrieve(collection, genai_client, question: str, top_k: int) -> Tuple[List[dict], bool]:
    # Retrieve similar chunks from Chroma.
    q_emb = embed_query(genai_client, question)
    res = collection.query(
        query_embeddings=[q_emb],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids = res["ids"][0]
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]

    chunks: List[dict] = []
    for _id, doc, meta, dist in zip(ids, docs, metas, dists):
        if not doc:
            continue
        sim = 1.0 - float(dist) if dist is not None else 0.0
        chunks.append({"id": _id, "doc": doc, "meta": meta or {}, "sim": sim})

    good = [c for c in chunks if c["sim"] >= config.MIN_SIMILARITY]
    good.sort(key=lambda x: x["sim"], reverse=True)
    return good, bool(good)


def build_context(chunks: List[dict]) -> str:
    # Build a compact context block for the prompt.
    lines: List[str] = []
    for idx, c in enumerate(chunks[: config.MAX_CONTEXT_CHUNKS], start=1):
        m = c["meta"] or {}
        txt = c["doc"][: config.MAX_CHARS_PER_CHUNK]
        lines.append(
            f"[CHUNK {idx}]\n"
            f"URL: {m.get('url','')}\n"
            f"TITLE: {m.get('title','')}\n"
            f"SOURCE_FILE: {m.get('source_file','')}\n"
            f"CHUNK_INDEX: {m.get('chunk_index','')}\n"
            f"SIMILARITY: {c['sim']:.3f}\n"
            f"TEXT:\n{txt}\n"
        )
    return "\n---\n".join(lines)


def make_prompt(question: str, context: str) -> str:
    # Build the final model prompt.
    return f"{config.SYSTEM_RULES}\n\nCONTEXT:\n{context}\n\nQUESTION:\n{question}\n\nANSWER:\n"

