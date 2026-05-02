"""
preprocess.py
=============
Stage 2 — Arabic preprocessing pipeline for the Youm7 corpus.

Reads:  output/youm7_corpus.json
Writes: output/youm7_chunks.json
        output/youm7_chunks.csv

For each document it:
  1. Cleans the body (HTML strip, Arabic normalization, URL/email removal,
     punctuation filtering, whitespace collapse).
  2. Splits the cleaned body into 200-word chunks with 50-word overlap.
  3. Emits one record per chunk with full metadata.
"""

import csv
import json
import logging
import os
import re
import sys
from typing import List

from bs4 import BeautifulSoup
from pyarabic import araby

# UTF-8 console for Arabic on Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("preprocess")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INPUT_PATH = os.path.join("output", "youm7_corpus.json")
OUT_JSON = os.path.join("output", "youm7_chunks.json")
OUT_CSV = os.path.join("output", "youm7_chunks.csv")

CHUNK_SIZE = 200    # words
CHUNK_OVERLAP = 50  # words

ALEF_VARIANTS = "أإآٱ"
TEH_MARBUTA = "ة"

# Patterns
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
WHITESPACE_RE = re.compile(r"\s+")

# Keep: Arabic letters (U+0600–U+06FF), Arabic Supplement (U+0750–U+077F),
# Latin letters, ASCII + Arabic-Indic digits, whitespace, and the three
# allowed Arabic punctuation marks. Everything else is removed.
KEEP_RE = re.compile(
    r"[^"
    r"؀-ۿ"      # Arabic block
    r"ݐ-ݿ"      # Arabic Supplement
    r"a-zA-Z"             # Latin letters (brand names like iPhone)
    r"0-9٠-٩"   # ASCII + Arabic-Indic digits
    r"،؟؛"                # allowed Arabic punctuation
    r"\s"                 # whitespace
    r"]+"
)

CSV_COLUMNS = [
    "source_doc_id", "chunk_index", "site", "source_name", "category",
    "url", "title", "language", "word_count", "char_count",
    "scraped_at", "chunk_text",
]


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

def strip_html(text: str) -> str:
    """Remove any leftover HTML tags using BeautifulSoup."""
    if "<" not in text:
        return text
    return BeautifulSoup(text, "lxml").get_text(" ", strip=True)


def normalize_arabic(text: str) -> str:
    """Normalize Alef variants → ا, Teh Marbuta → ه, strip tashkeel & tatweel."""
    # Alef variants (أ إ آ ٱ) → ا
    text = re.sub(f"[{ALEF_VARIANTS}]", "ا", text)
    # Teh Marbuta (ة) → ه
    text = text.replace(TEH_MARBUTA, "ه")
    # Strip tashkeel (ً–ٟ) — pyarabic handles the standard range.
    text = araby.strip_tashkeel(text)
    # Strip tatweel (ـ).
    text = araby.strip_tatweel(text)
    return text


def clean_body(text: str) -> str:
    """Run the full cleaning pipeline on one body string."""
    if not text:
        return ""
    text = strip_html(text)
    text = URL_RE.sub(" ", text)
    text = EMAIL_RE.sub(" ", text)
    text = normalize_arabic(text)
    text = KEEP_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping word-windows of `size` with `overlap` words shared."""
    words = text.split()
    if not words:
        return []
    if len(words) <= size:
        return [" ".join(words)]

    step = size - overlap
    if step <= 0:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")

    chunks = []
    i = 0
    while i < len(words):
        window = words[i:i + size]
        chunks.append(" ".join(window))
        if i + size >= len(words):
            break
        i += step
    return chunks


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def load_corpus(path: str) -> list:
    """Read the input corpus JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_chunk_records(documents: list) -> list:
    """Clean every body, chunk it, and emit one record per chunk."""
    records = []
    for doc_id, doc in enumerate(documents):
        cleaned = clean_body(doc.get("body", ""))
        if not cleaned:
            logger.warning("Doc %d produced empty body after cleaning: %s",
                           doc_id, doc.get("url", ""))
            continue
        for chunk_idx, chunk in enumerate(chunk_text(cleaned)):
            records.append({
                "source_doc_id": doc_id,
                "chunk_index": chunk_idx,
                "site": doc.get("site", ""),
                "source_name": doc.get("source_name", ""),
                "category": doc.get("category", ""),
                "url": doc.get("url", ""),
                "title": doc.get("title", ""),
                "language": "ar",
                "chunk_text": chunk,
                "word_count": len(chunk.split()),
                "char_count": len(chunk),
                "scraped_at": doc.get("scraped_at", ""),
            })
    return records


def save_json(records: list, path: str) -> None:
    """Write all chunk records to JSON with real Arabic characters."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    logger.info("Wrote %s (%d records)", path, len(records))


def save_csv(records: list, path: str) -> None:
    """Write all chunk records to CSV using utf-8-sig for Excel."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for rec in records:
            writer.writerow({col: rec.get(col, "") for col in CSV_COLUMNS})
    logger.info("Wrote %s (%d records)", path, len(records))


def print_summary(records: list, n_docs: int) -> None:
    """Print a stats summary: total, avg size, per-category counts."""
    total = len(records)
    if total == 0:
        print("No chunks produced.")
        return
    avg_words = sum(r["word_count"] for r in records) / total
    avg_chars = sum(r["char_count"] for r in records) / total

    by_cat = {}
    for r in records:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1

    print("=" * 60)
    print("Youm7 Preprocessing — Summary")
    print("=" * 60)
    print(f"Source documents     : {n_docs}")
    print(f"Total chunks         : {total}")
    print(f"Avg chunk size (words): {avg_words:.1f}")
    print(f"Avg chunk size (chars): {avg_chars:.1f}")
    print(f"Chunk size config    : {CHUNK_SIZE} words, overlap {CHUNK_OVERLAP}")
    print()
    print("Chunks by category:")
    for cat, count in sorted(by_cat.items(), key=lambda kv: -kv[1]):
        print(f"  - {cat}: {count}")
    print("=" * 60)


def main() -> None:
    """Run end-to-end: load, clean, chunk, write, summarize."""
    if not os.path.exists(INPUT_PATH):
        logger.error("Input not found: %s — run youm7_scraper.py first.", INPUT_PATH)
        sys.exit(1)

    logger.info("Loading %s", INPUT_PATH)
    documents = load_corpus(INPUT_PATH)
    logger.info("Loaded %d documents", len(documents))

    records = build_chunk_records(documents)
    if not records:
        logger.error("No chunks were produced — aborting.")
        sys.exit(1)

    save_json(records, OUT_JSON)
    save_csv(records, OUT_CSV)
    print_summary(records, len(documents))


if __name__ == "__main__":
    main()
