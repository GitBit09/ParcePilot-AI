"""
RAG Indexer: Builds a FAISS vector index from all PDF documents.
Uses Google Gemini text-embedding-004 for embeddings (no local model needed).
Run once with: python -m rag.indexer
Skips deprecated documents from query results (still indexed but flagged).
"""

import os
import pickle
import numpy as np
import pdfplumber
import faiss
from pathlib import Path
from dotenv import load_dotenv
import google.genai as genai

load_dotenv()

DATA_DIR = os.getenv("DATA_DIR", "../data/AI Agent Assessment - Candidate Pack")
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./rag/faiss_index")

CHUNK_SIZE = 400  # characters per chunk
CHUNK_OVERLAP = 80

# Document metadata
DOC_METADATA = {
    "01_Support_Policy_v3_CURRENT.pdf": {
        "label": "Support Policy v3 (Current)",
        "priority": 2,
        "status": "CURRENT",
    },
    "02_Support_Policy_v2_DEPRECATED.pdf": {
        "label": "Support Policy v2 (DEPRECATED)",
        "priority": 99,
        "status": "DEPRECATED",
    },
    "03_Cancellation_and_Service_Credit_SOP_v4.pdf": {
        "label": "Cancellation & Service Credit SOP v4 (Current)",
        "priority": 2,
        "status": "CURRENT",
    },
    "04_Product_Operations_Guide_and_Known_Issues.pdf": {
        "label": "Product Operations Guide (Current)",
        "priority": 3,
        "status": "CURRENT",
    },
    "05_Northstar_Logistics_Enterprise_Agreement.pdf": {
        "label": "Northstar Enterprise Agreement",
        "priority": 1,
        "status": "ACTIVE",
        "applies_to": "ACCT-001",
    },
    "06_LumenWorks_Service_Agreement.pdf": {
        "label": "LumenWorks Service Agreement",
        "priority": 1,
        "status": "ACTIVE",
        "applies_to": "ACCT-002",
    },
}


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def embed_texts(client: genai.Client, texts: list[str]) -> np.ndarray:
    """Embed a list of texts using gemini-embedding-2."""
    vectors = []
    for i, text in enumerate(texts):
        result = client.models.embed_content(
            model="gemini-embedding-2",
            contents=text,
        )
        vectors.append(result.embeddings[0].values)
        if (i + 1) % 10 == 0:
            print(f"  Embedded {i + 1}/{len(texts)} chunks...")
    return np.array(vectors, dtype="float32")


def build_index():
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")

    client = genai.Client(api_key=api_key)
    os.makedirs(FAISS_INDEX_PATH, exist_ok=True)

    all_chunks = []   # list of text strings
    all_meta = []     # list of metadata dicts

    for pdf_file, meta in DOC_METADATA.items():
        pdf_path = os.path.join(DATA_DIR, pdf_file)
        if not os.path.exists(pdf_path):
            print(f"[!] Not found: {pdf_file}")
            continue

        print(f"[PDF] Indexing: {pdf_file}")
        with pdfplumber.open(pdf_path) as doc:
            full_text = ""
            for page in doc.pages:
                full_text += (page.extract_text() or "") + "\n"

        chunks = chunk_text(full_text)
        for i, chunk in enumerate(chunks):
            if chunk.strip():
                all_chunks.append(chunk)
                all_meta.append({
                    "source": pdf_file,
                    "chunk_id": i,
                    "label": meta["label"],
                    "priority": meta["priority"],
                    "status": meta["status"],
                    "applies_to": meta.get("applies_to"),
                    "text": chunk,
                })

    print(f"\n[ENC] Embedding {len(all_chunks)} chunks with Gemini text-embedding-004...")
    embeddings = embed_texts(client, all_chunks)

    # Build FAISS index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # Save
    faiss.write_index(index, os.path.join(FAISS_INDEX_PATH, "index.faiss"))
    with open(os.path.join(FAISS_INDEX_PATH, "metadata.pkl"), "wb") as f:
        pickle.dump(all_meta, f)

    print(f"[OK] FAISS index built: {len(all_chunks)} chunks, dim={dim}")
    print(f"   Saved to: {FAISS_INDEX_PATH}")


if __name__ == "__main__":
    build_index()
