"""
embed.py
========
Stage 3 — Model selection, embedding generation, and FAISS search index
for the Youm7 Arabic QA system.

Pipeline:
  output/youm7_chunks.json
        │
        ▼  paraphrase-multilingual-MiniLM-L12-v2 (384-dim, normalized)
        │
        ├──► output/youm7_index.faiss     (IndexFlatIP, cosine similarity)
        └──► output/youm7_metadata.json   (FAISS pos -> chunk metadata)

Run with:
    python embed.py
"""

import json
import logging
import os
import sys

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# UTF-8 console for Arabic on Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBED_BATCH_SIZE = 32
EMBED_DIM = 384

OUTPUT_DIR = "output"
CHUNKS_PATH = os.path.join(OUTPUT_DIR, "youm7_chunks.json")
INDEX_PATH = os.path.join(OUTPUT_DIR, "youm7_index.faiss")
METADATA_PATH = os.path.join(OUTPUT_DIR, "youm7_metadata.json")

METADATA_FIELDS = [
    "source_doc_id", "chunk_index", "site", "source_name", "category",
    "url", "title", "chunk_text", "word_count", "scraped_at",
]

TEST_QUESTIONS = [
    "ما هو سعر الذهب في مصر اليوم؟",
    "ما هي أحدث أخبار الأهلي والزمالك؟",
    "ما هي أعراض أمراض القلب وكيف تتجنبها؟",
    "ما هي أحدث التطورات في الذكاء الاصطناعي؟",
    "ما هي توقعات الطقس في مصر؟",
]


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("embed")
# Quiet down noisy underlying libs so the run output stays readable.
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------

def ensure_output_dir() -> None:
    """Create the output/ directory if it does not already exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_chunks(path: str) -> list:
    """Load the Stage-2 chunk records from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_metadata(metadata: list, path: str) -> None:
    """Persist the FAISS-position -> chunk metadata mapping as JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    logger.info("Wrote %s (%d entries)", path, len(metadata))


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def load_model(name: str = MODEL_NAME) -> SentenceTransformer:
    """Download (first time only) and return the sentence-transformer model."""
    logger.info("Loading model: %s", name)
    return SentenceTransformer(name)


def build_combined_texts(chunks: list) -> list:
    """Concatenate `title` and `chunk_text` so the model sees both contexts."""
    return [f"{c.get('title', '')} {c.get('chunk_text', '')}" for c in chunks]


def embed_texts(model: SentenceTransformer, texts: list) -> np.ndarray:
    """Encode texts to L2-normalized 384-dim float32 vectors via batching."""
    embeddings = model.encode(
        texts,
        batch_size=EMBED_BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embeddings.astype(np.float32)


# ---------------------------------------------------------------------------
# FAISS index
# ---------------------------------------------------------------------------

def build_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    """Create an inner-product FAISS index (cosine sim on normalized vectors)."""
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index


def build_metadata(chunks: list) -> list:
    """Project each chunk into a metadata record keyed by its FAISS position."""
    out = []
    for i, c in enumerate(chunks):
        record = {"index_id": i}
        for f in METADATA_FIELDS:
            record[f] = c.get(f, "")
        out.append(record)
    return out


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search(
    question: str,
    index: faiss.Index,
    metadata: list,
    model: SentenceTransformer,
    top_k: int = 5,
) -> list:
    """Embed the question and return the top_k metadata records by cosine score.

    Each result dict contains: rank, score, category, url, title,
    chunk_text, chunk_index.
    """
    q_vec = model.encode(
        [question],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)

    scores, ids = index.search(q_vec, top_k)

    results = []
    for rank, (score, idx) in enumerate(zip(scores[0], ids[0]), start=1):
        if idx < 0:  # FAISS returns -1 when fewer than top_k vectors exist.
            continue
        m = metadata[idx]
        results.append({
            "rank": rank,
            "score": float(score),
            "category": m.get("category", ""),
            "url": m.get("url", ""),
            "title": m.get("title", ""),
            "chunk_text": m.get("chunk_text", ""),
            "chunk_index": m.get("chunk_index", 0),
        })
    return results


# ---------------------------------------------------------------------------
# Test runner / output formatting
# ---------------------------------------------------------------------------

def print_results(question: str, results: list) -> None:
    """Pretty-print a question and its ranked search results."""
    bar = "═" * 70
    print(bar)
    print(f"Q: {question}")
    print(bar)
    if not results:
        print("(no results)")
        return
    for r in results:
        print(f"Rank {r['rank']} | Score: {r['score']:.4f} | "
              f"Category: {r['category']}")
        print(f"Title : {r['title']}")
        snippet = r["chunk_text"][:200].replace("\n", " ")
        print(f"Answer: {snippet}...")
        print(f"URL   : {r['url']}")
        print("─" * 70)
    print()


def run_tests(index: faiss.Index, metadata: list,
              model: SentenceTransformer) -> None:
    """Run the built-in test questions and print top-5 results for each."""
    for q in TEST_QUESTIONS:
        results = search(q, index, metadata, model, top_k=5)
        print_results(q, results)


def print_summary(n_chunks: int, n_vectors: int) -> None:
    """Print the final Stage-3 completion banner."""
    lines = [
        "╔══════════════════════════════════════════════════╗",
        "║          STAGE 3 COMPLETE ✅                     ║",
        "╠══════════════════════════════════════════════════╣",
        f"║  Model    : {MODEL_NAME:<37}║",
        f"║  Chunks   : {n_chunks:<37}║",
        f"║  Vectors  : {n_vectors:<37}║",
        f"║  Dimension: {EMBED_DIM:<37}║",
        "╠══════════════════════════════════════════════════╣",
        "║  Files saved:                                    ║",
        f"║  • {INDEX_PATH:<46}║",
        f"║  • {METADATA_PATH:<46}║",
        "╚══════════════════════════════════════════════════╝",
    ]
    print("\n".join(lines))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run end-to-end: load chunks, embed, index, save, then run test queries."""
    ensure_output_dir()

    if not os.path.exists(CHUNKS_PATH):
        print("ERROR: youm7_chunks.json not found. Run preprocess.py first.")
        sys.exit(1)

    chunks = load_chunks(CHUNKS_PATH)
    logger.info("Loaded %d chunks from %s", len(chunks), CHUNKS_PATH)
    if not chunks:
        logger.error("Chunk file is empty — nothing to embed.")
        sys.exit(1)

    model = load_model(MODEL_NAME)

    texts = build_combined_texts(chunks)
    logger.info("Encoding %d combined texts (title + chunk_text)...", len(texts))
    embeddings = embed_texts(model, texts)
    logger.info("Embedding shape: %s, dtype=%s",
                embeddings.shape, embeddings.dtype)

    index = build_faiss_index(embeddings)
    faiss.write_index(index, INDEX_PATH)
    logger.info("Wrote %s (%d vectors, dim %d)",
                INDEX_PATH, index.ntotal, embeddings.shape[1])

    metadata = build_metadata(chunks)
    save_metadata(metadata, METADATA_PATH)

    print()
    logger.info("Running %d built-in test questions...", len(TEST_QUESTIONS))
    print()
    run_tests(index, metadata, model)

    print_summary(n_chunks=len(chunks), n_vectors=index.ntotal)


if __name__ == "__main__":
    main()
