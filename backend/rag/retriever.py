"""
RAG Retriever: Semantic search over the FAISS index.
Returns top-k chunks with source metadata and priority ranking.
"""

import os
import pickle
import numpy as np
import faiss
from dotenv import load_dotenv

load_dotenv()

FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./rag/faiss_index")

_model = None
_index = None
_metadata = None


def _load():
    global _model, _index, _metadata
    if _index is None:
        from sentence_transformers import SentenceTransformer  # lazy: avoids 55s PyTorch load at startup
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        _index = faiss.read_index(os.path.join(FAISS_INDEX_PATH, "index.faiss"))
        with open(os.path.join(FAISS_INDEX_PATH, "metadata.pkl"), "rb") as f:
            _metadata = pickle.load(f)


def search(query: str, top_k: int = 6, account_id: str | None = None, include_deprecated: bool = False) -> list[dict]:
    """
    Search the FAISS index for relevant document chunks.

    Args:
        query: Natural language query
        top_k: Number of results to return
        account_id: If provided, customer-agreement docs for other accounts are filtered out
        include_deprecated: If False (default), deprecated docs are excluded from results

    Returns:
        List of result dicts sorted by priority (ascending = higher authority first)
    """
    _load()

    query_vec = _model.encode([query], convert_to_numpy=True).astype("float32")
    distances, indices = _index.search(query_vec, top_k * 3)  # over-fetch for filtering

    results = []
    seen_chunks = set()

    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        meta = _metadata[idx]

        # Skip deprecated docs
        if not include_deprecated and meta["status"] == "DEPRECATED":
            continue

        # Account scoping: if user is a customer, filter out other customers' agreements
        if account_id and meta.get("applies_to"):
            if meta["applies_to"] != account_id:
                continue

        # De-duplicate nearly identical chunks
        chunk_key = meta["source"] + str(meta["chunk_id"])
        if chunk_key in seen_chunks:
            continue
        seen_chunks.add(chunk_key)

        results.append({
            "text": meta["text"],
            "source": meta["source"],
            "label": meta["label"],
            "priority": meta["priority"],
            "status": meta["status"],
            "applies_to": meta.get("applies_to"),
            "distance": float(dist),
        })

        if len(results) >= top_k:
            break

    # Sort by priority (lower = higher authority), then by distance
    results.sort(key=lambda x: (x["priority"], x["distance"]))
    return results


def format_for_prompt(results: list[dict]) -> str:
    """Format search results for inclusion in LLM prompt."""
    if not results:
        return "No relevant documents found."

    parts = []
    for r in results:
        priority_label = {1: "CUSTOMER AGREEMENT (highest authority)", 2: "CURRENT POLICY/SOP",
                          3: "PRODUCT GUIDE", 9: "HISTORICAL CONTEXT (may be wrong)", 99: "DEPRECATED"
                          }.get(r["priority"], "UNKNOWN")
        parts.append(
            f"[Source: {r['label']} | Authority: {priority_label}]\n{r['text']}"
        )

    return "\n\n---\n\n".join(parts)
