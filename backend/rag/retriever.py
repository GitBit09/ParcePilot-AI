"""
RAG Retriever: Semantic search over the FAISS index.
Uses Google Gemini text-embedding-004 for query embedding.
Returns top-k chunks with source metadata and priority ranking.
"""

import os
import pickle
import numpy as np
import faiss
from dotenv import load_dotenv

load_dotenv()

FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./rag/faiss_index")

_index = None
_metadata = None


def _embed(texts: list[str]) -> np.ndarray:
    """Embed texts using gemini-embedding-2 (lazy import)."""
    import google.genai as genai
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    vectors = []
    for text in texts:
        result = client.models.embed_content(
            model="gemini-embedding-2",
            contents=text,
        )
        vectors.append(result.embeddings[0].values)
    return np.array(vectors, dtype="float32")


def _load():
    global _index, _metadata
    if _index is None:
        _index = faiss.read_index(os.path.join(FAISS_INDEX_PATH, "index.faiss"))
        with open(os.path.join(FAISS_INDEX_PATH, "metadata.pkl"), "rb") as f:
            _metadata = pickle.load(f)


def search(query: str, top_k: int = 6, account_id: str = None, include_deprecated: bool = False) -> list[dict]:
    """Semantic search over indexed PDF chunks."""
    _load()
    q_emb = _embed([query])
    D, I = _index.search(q_emb, top_k * 3)  # over-fetch to allow filtering

    results = []
    seen = set()
    for idx in I[0]:
        if idx < 0 or idx >= len(_metadata):
            continue
        chunk = _metadata[idx]

        # Filter deprecated unless explicitly included
        if not include_deprecated and chunk.get("status") == "DEPRECATED":
            continue

        # Filter by account agreement if account_id provided
        applies_to = chunk.get("applies_to")
        if applies_to and account_id and applies_to != account_id:
            continue

        key = (chunk["source"], chunk["chunk_id"])
        if key in seen:
            continue
        seen.add(key)

        results.append(chunk)
        if len(results) >= top_k:
            break

    return results


def format_for_prompt(chunks: list[dict]) -> str:
    """Format retrieved chunks for inclusion in the system prompt."""
    if not chunks:
        return "No relevant documents found."

    lines = []
    for i, chunk in enumerate(chunks, 1):
        label = chunk.get("label", chunk["source"])
        status = chunk.get("status", "")
        applies_to = chunk.get("applies_to")
        scope = f" [Applies to: {applies_to}]" if applies_to else ""
        deprecated_flag = " ⚠️ DEPRECATED — DO NOT USE" if status == "DEPRECATED" else ""
        lines.append(f"[{i}] Source: {label}{scope}{deprecated_flag}")
        lines.append(chunk["text"].strip())
        lines.append("")

    return "\n".join(lines)
