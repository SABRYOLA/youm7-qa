"""
answer.py
=========
Stage 4 — Extractive Arabic QA over the Youm7 corpus.

Public API:
  load_resources()  → (model, index, metadata)  — loads once, caches at module level
  retrieve(...)     → list of ranked chunk dicts
  ask(...)          → final answer dict (retrieve → extract → format)

Both `retrieve` and `ask` accept resources as keyword args; if omitted, the
module-level cache is used (lazy-loaded on first call). This lets a server
load resources once at startup and pass them on every request, while still
allowing plain `python answer.py` standalone use.

Run with:
    python answer.py
"""

import json
import logging
import os
import re
import sys
from typing import Optional

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pyarabic import araby

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

OUTPUT_DIR = "output"
INDEX_PATH = os.path.join(OUTPUT_DIR, "youm7_index.faiss")
METADATA_PATH = os.path.join(OUTPUT_DIR, "youm7_metadata.json")
ANSWERS_PATH = os.path.join(OUTPUT_DIR, "youm7_answers.json")

CONFIDENCE_THRESHOLD = 0.30
HIGH_CONFIDENCE = 0.65
MEDIUM_CONFIDENCE = 0.40
TOP_K = 5
RELATED_LIMIT = 3
MIN_QWORD_LEN = 2
TOP_SENTENCES = 2
FALLBACK_CHARS = 200

NO_ANSWER_MSG = "عذراً، لا تتوفر معلومات كافية للإجابة على هذا السؤال"

ALEF_VARIANTS = "أإآٱ"
TEH_MARBUTA = "ة"
SENTENCE_SPLIT_RE = re.compile(r"[،.؟؛\n]+")

TEST_QUESTIONS = [
    "ما هو سعر الذهب عيار 21 في مصر اليوم؟",
    "ما هي أسباب أمراض القلب؟",
    "ما آخر أخبار الذكاء الاصطناعي وآبل؟",
    "ما هي مواعيد مباريات الدوري المصري؟",
    "ما هي نصائح لتقوية العضلات؟",
]


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("answer")
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Module-level resource cache
# ---------------------------------------------------------------------------

_resources: Optional[tuple] = None  # (model, index, metadata)


def load_resources(
    model_name: str = MODEL_NAME,
    index_path: str = INDEX_PATH,
    metadata_path: str = METADATA_PATH,
) -> tuple:
    """Load (or reload) the embedding model, FAISS index, and metadata.

    Caches the triple at module level so subsequent `ask`/`retrieve` calls
    can omit resources. Returns (model, index, metadata).
    """
    global _resources
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"FAISS index not found: {index_path}")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")

    logger.info("Loading model: %s", model_name)
    model = SentenceTransformer(model_name)

    logger.info("Loading FAISS index: %s", index_path)
    index = faiss.read_index(index_path)

    logger.info("Loading metadata: %s", metadata_path)
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    logger.info("Resources ready: %d vectors, %d metadata entries",
                index.ntotal, len(metadata))
    _resources = (model, index, metadata)
    return _resources


def _resolve_resources(model, index, metadata) -> tuple:
    """Return the provided resources, or fall back to the cached triple."""
    if model is not None and index is not None and metadata is not None:
        return model, index, metadata
    if _resources is None:
        load_resources()
    return _resources


# ---------------------------------------------------------------------------
# Arabic normalization (matches what Stage 2 applied to chunk_text)
# ---------------------------------------------------------------------------

def normalize_ar(text: str) -> str:
    """Normalize Alef variants → ا, Teh Marbuta → ه, strip tashkeel & tatweel."""
    if not text:
        return ""
    text = re.sub(f"[{ALEF_VARIANTS}]", "ا", text)
    text = text.replace(TEH_MARBUTA, "ه")
    text = araby.strip_tashkeel(text)
    text = araby.strip_tatweel(text)
    return text


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve(
    question: str,
    top_k: int = TOP_K,
    apply_threshold: bool = True,
    *,
    model: Optional[SentenceTransformer] = None,
    index: Optional[faiss.Index] = None,
    metadata: Optional[list] = None,
) -> list:
    """Embed the question and return top_k FAISS-ranked chunk dicts.

    When `apply_threshold` is True (default) and the best score is below
    CONFIDENCE_THRESHOLD, returns []. Set False for raw search.

    Each result dict contains: rank, score, title, category, url,
    chunk_text, chunk_index, scraped_at.
    """
    model, index, metadata = _resolve_resources(model, index, metadata)

    q_vec = model.encode(
        [question],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)

    scores, ids = index.search(q_vec, top_k)

    if apply_threshold:
        if len(scores[0]) == 0 or float(scores[0][0]) < CONFIDENCE_THRESHOLD:
            logger.info("Low confidence — no relevant chunks found")
            return []

    results = []
    for rank, (score, idx) in enumerate(zip(scores[0], ids[0]), start=1):
        if idx < 0:
            continue
        m = metadata[idx]
        results.append({
            "rank": rank,
            "score": float(score),
            "title": m.get("title", ""),
            "category": m.get("category", ""),
            "url": m.get("url", ""),
            "chunk_text": m.get("chunk_text", ""),
            "chunk_index": m.get("chunk_index", 0),
            "scraped_at": m.get("scraped_at", ""),
        })
    return results


# ---------------------------------------------------------------------------
# Extractive answer
# ---------------------------------------------------------------------------

def extract_answer(question: str, chunk_text: str) -> str:
    """Pick the 2 sentences with the most overlap with the question's keywords."""
    if not chunk_text:
        return ""

    norm_q = normalize_ar(question)
    q_words = [
        w for w in re.findall(r"\w+", norm_q, flags=re.UNICODE)
        if len(w) > MIN_QWORD_LEN
    ]

    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(chunk_text) if s.strip()]
    if not sentences:
        return chunk_text[:FALLBACK_CHARS].strip()

    scored = []
    for i, sent in enumerate(sentences):
        score = sum(1 for w in q_words if w in sent)
        scored.append((score, i, sent))

    scored.sort(key=lambda t: (-t[0], t[1]))

    if scored[0][0] == 0:
        return chunk_text[:FALLBACK_CHARS].strip()

    top = [t for t in scored[:TOP_SENTENCES] if t[0] > 0]
    top.sort(key=lambda t: t[1])
    return "، ".join(t[2] for t in top).strip()


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def confidence_label(score: float) -> str:
    """Map a numeric cosine score to its Arabic confidence label."""
    if score >= HIGH_CONFIDENCE:
        return "عالية"
    if score >= MEDIUM_CONFIDENCE:
        return "متوسطة"
    if score >= CONFIDENCE_THRESHOLD:
        return "منخفضة"
    return "لا توجد نتائج"


def format_answer(
    question: str,
    extracted: str,
    top_chunk: dict,
    all_results: list,
) -> dict:
    """Assemble the final answer dict with confidence and related sources."""
    related = []
    for r in all_results[1:1 + RELATED_LIMIT]:
        related.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "score": round(float(r.get("score", 0.0)), 4),
            "category": r.get("category", ""),
        })

    score = float(top_chunk.get("score", 0.0))
    return {
        "question": question,
        "answer": extracted,
        "confidence": round(score, 2),
        "confidence_label": confidence_label(score),
        "source_title": top_chunk.get("title", ""),
        "source_url": top_chunk.get("url", ""),
        "source_category": top_chunk.get("category", ""),
        "related_sources": related,
        "scraped_at": top_chunk.get("scraped_at", ""),
    }


def empty_answer(question: str) -> dict:
    """Build the placeholder dict returned when retrieval yields nothing."""
    return {
        "question": question,
        "answer": NO_ANSWER_MSG,
        "confidence": 0.0,
        "confidence_label": "لا توجد نتائج",
        "source_title": "",
        "source_url": "",
        "source_category": "",
        "related_sources": [],
        "scraped_at": "",
    }


# ---------------------------------------------------------------------------
# Main QA
# ---------------------------------------------------------------------------

def ask(
    question: str,
    top_k: int = TOP_K,
    *,
    model: Optional[SentenceTransformer] = None,
    index: Optional[faiss.Index] = None,
    metadata: Optional[list] = None,
) -> dict:
    """Run retrieve → extract → format for one question and return the answer dict.

    Resources may be passed in for a server (loaded once at startup) or
    omitted to use the lazy-loaded module-level cache.
    """
    model, index, metadata = _resolve_resources(model, index, metadata)
    results = retrieve(
        question,
        top_k=top_k,
        model=model, index=index, metadata=metadata,
    )
    if not results:
        return empty_answer(question)
    top = results[0]
    extracted = extract_answer(question, top["chunk_text"])
    return format_answer(question, extracted, top, results)


# ---------------------------------------------------------------------------
# Pretty print
# ---------------------------------------------------------------------------

def print_answer(ans: dict) -> None:
    """Print one answer dict using the box-drawing template from the spec."""
    print("╔══════════════════════════════════════════════════╗")
    print(f"║  السؤال  : {ans['question']}")
    print(f"║  الإجابة : {ans['answer']}")
    print(f"║  الثقة   : {ans['confidence_label']} ({ans['confidence']:.2f})")
    print(f"║  المصدر  : {ans['source_title']}")
    print(f"║  الرابط  : {ans['source_url']}")
    if ans["related_sources"]:
        print("╠══════════════════════════════════════════════════╣")
        print("║  مصادر ذات صلة:")
        for rs in ans["related_sources"]:
            print(f"║  • {rs['title']} — {rs['score']:.4f}")
    print("╚══════════════════════════════════════════════════╝")
    print()


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------

def save_answers(answers: list, path: str) -> None:
    """Persist the test-question answers to disk as JSON with real Arabic."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(answers, f, ensure_ascii=False, indent=2)
    logger.info("Wrote %s (%d answers)", path, len(answers))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Load resources, run the 5 test questions, save answers."""
    if not os.path.exists(INDEX_PATH):
        print(f"ERROR: {INDEX_PATH} not found. Run embed.py first.")
        sys.exit(1)
    if not os.path.exists(METADATA_PATH):
        print(f"ERROR: {METADATA_PATH} not found. Run embed.py first.")
        sys.exit(1)

    model, index, metadata = load_resources()

    print()
    answers = []
    for q in TEST_QUESTIONS:
        ans = ask(q, model=model, index=index, metadata=metadata)
        print_answer(ans)
        answers.append(ans)

    save_answers(answers, ANSWERS_PATH)


if __name__ == "__main__":
    main()
