"""
embed_and_retrieve.py  —  Milestone 4
Embeds chunks from data/chunks.json using all-MiniLM-L6-v2 (local, no API key),
stores them in ChromaDB with source metadata, and exposes a retrieve() function
for the generation step.

Usage
-----
Build / rebuild the vector store:
    python embed_and_retrieve.py --build

Interactive query (for testing):
    python embed_and_retrieve.py --query "where can I get food near UT Dallas"
"""

import argparse
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

# ── Config ────────────────────────────────────────────────────────────────────
CHUNKS_PATH   = Path("data/chunks.json")
CHROMA_DIR    = Path("data/chroma")
COLLECTION    = "housing_guide"
MODEL_NAME    = "all-MiniLM-L6-v2"
TOP_K         = 5   # k=5 tested against all evaluation questions — do not raise to 7.
                    # Higher k dilutes context: Q3/Q4 (Dallas Life intake) drop to rank 7
                    # with k=7 and never surface the correct chunk. Specificity in the
                    # query string matters more than k: include the org name + key terms
                    # (e.g. "Dallas Life shelter intake hours monday friday") to pull the
                    # right chunk to rank 1. The generation prompt should do this
                    # automatically when the user names a specific organization.


# ── Embedding + store ─────────────────────────────────────────────────────────

def embed_and_store(chunks_path: Path = CHUNKS_PATH) -> None:
    """Embed every chunk and upsert into ChromaDB with full source metadata."""
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    print(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print(f"Embedding {len(chunks)} chunks...")
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_list=True)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    # Drop and recreate so a re-run always reflects the latest chunks.json
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    collection.upsert(
        ids=[c["chunk_id"] for c in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {
                "source":      c["source"],
                "url":         c["url"],
                "token_count": c["token_count"],
            }
            for c in chunks
        ],
    )
    print(f"Stored {len(chunks)} chunks → {CHROMA_DIR}")


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """
    Embed the query and return the top-k most similar chunks.

    Each result dict contains:
        text        — the chunk text
        source      — human-readable source name
        url         — original URL or file path
        chunk_id    — unique chunk identifier
        score       — cosine similarity (0–1, higher = more relevant)
    """
    model = SentenceTransformer(MODEL_NAME)
    query_embedding = model.encode(query, convert_to_list=True)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(COLLECTION)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append(
            {
                "text":        doc,
                "source":      meta["source"],
                "url":         meta["url"],
                "chunk_id":    results["ids"][0][len(hits)],
                "score":       round(1 - dist, 4),  # cosine distance → similarity
            }
        )

    return hits


# ── CLI ───────────────────────────────────────────────────────────────────────

def _print_results(hits: list[dict]) -> None:
    for i, h in enumerate(hits, 1):
        print(f"\n{'─'*60}")
        print(f"Result {i}  |  {h['source']}  |  score: {h['score']}  |  {h['chunk_id']}")
        print(f"URL: {h['url']}")
        print()
        print(h["text"])
    print(f"\n{'─'*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true",
                        help="Embed chunks.json and (re)build the ChromaDB collection")
    parser.add_argument("--query", type=str, default="",
                        help="Query string to retrieve relevant chunks")
    parser.add_argument("--k", type=int, default=TOP_K,
                        help=f"Number of results to return (default {TOP_K})")
    args = parser.parse_args()

    if args.build:
        embed_and_store()

    if args.query:
        hits = retrieve(args.query, k=args.k)
        print(f"\nTop {len(hits)} results for: \"{args.query}\"\n")
        _print_results(hits)

    if not args.build and not args.query:
        parser.print_help()
