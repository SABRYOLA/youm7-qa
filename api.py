"""
api.py
======
Stage 5 — FastAPI deployment of the Youm7 Arabic QA system.

Endpoints:
  GET  /          — welcome / endpoint index
  GET  /health    — system health (model + index loaded, sizes)
  POST /ask       — full QA: retrieve → extract → format
  POST /search    — raw FAISS search (no answer extraction, no threshold)

The model, FAISS index, and metadata are loaded once at startup via the
FastAPI lifespan context and stashed on app.state. Every request reuses
them — no per-request reloads.

Run with:
    python api.py
"""

import logging
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from answer import (
    ask,
    retrieve,
    load_resources,
    MODEL_NAME,
    INDEX_PATH,
    METADATA_PATH,
)

# UTF-8 console for Arabic on Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("api")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    """Body of POST /ask — an Arabic question and optional top_k."""
    question: str = Field(..., description="The question, in Arabic")
    top_k: int = Field(default=5, ge=1, le=10,
                       description="How many chunks to retrieve (1–10)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "ما هو سعر الذهب اليوم؟",
                "top_k": 5,
            }
        }
    }


class SearchRequest(BaseModel):
    """Body of POST /search — raw retrieval, no answer extraction."""
    query: str = Field(..., description="Free-text search query, in Arabic")
    top_k: int = Field(default=3, ge=1, le=10,
                       description="How many chunks to return (1–10)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "الذهب في مصر",
                "top_k": 3,
            }
        }
    }


class RelatedSource(BaseModel):
    """One related-source citation accompanying an answer."""
    title: str
    url: str
    score: float
    category: str


class AskResponse(BaseModel):
    """Final formatted answer returned by POST /ask."""
    question: str
    answer: str
    confidence: float
    confidence_label: str
    source_title: str
    source_url: str
    source_category: str
    related_sources: list[RelatedSource]
    scraped_at: str
    processing_time_ms: int


class SearchResultItem(BaseModel):
    """One ranked chunk inside a /search response."""
    rank: int
    score: float
    title: str
    category: str
    url: str
    chunk_preview: str
    chunk_index: int


class SearchResponse(BaseModel):
    """Body of POST /search response."""
    query: str
    total_results: int
    results: list[SearchResultItem]


# ---------------------------------------------------------------------------
# Lifespan — load resources once at startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model, FAISS index, and metadata once at server startup."""
    try:
        model, index, metadata = load_resources()
    except FileNotFoundError as exc:
        logger.error("Failed to load resources: %s", exc)
        logger.error("Run embed.py first to build the index and metadata.")
        raise

    app.state.model = model
    app.state.index = index
    app.state.metadata = metadata
    app.state.total_chunks = index.ntotal
    app.state.total_articles = len({m["source_doc_id"] for m in metadata})
    app.state.model_name = MODEL_NAME

    print("✅ Youm7 QA API is ready — model and index loaded")
    yield


# ---------------------------------------------------------------------------
# App + middleware
# ---------------------------------------------------------------------------

API_DESCRIPTION = (
    "نظام إجابة الأسئلة العربي مبني على نصوص اليوم السابع. يستخدم نموذج "
    "تضمين متعدد اللغات وفهرس FAISS لاسترجاع الإجابات الأكثر صلة.\n\n"
    "Arabic question-answering API over the Youm7 corpus. Uses the "
    "`paraphrase-multilingual-MiniLM-L12-v2` sentence-transformer to embed "
    "questions and a FAISS `IndexFlatIP` index for cosine-similarity retrieval, "
    "then extracts the most relevant sentences from the top-matching chunk."
)

app = FastAPI(
    title="Youm7 QA API — نظام الإجابة على الأسئلة",
    description=API_DESCRIPTION,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log each request with method, path, status, and latency."""
    t0 = time.time()
    response = await call_next(request)
    elapsed_ms = int((time.time() - t0) * 1000)
    logger.info("%s %s — %s — %dms",
                request.method, request.url.path,
                response.status_code, elapsed_ms)
    return response


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/",
    summary="Welcome / endpoint index",
    response_description="Welcome message and endpoint listing",
)
def root():
    """Return the welcome message and endpoint index."""
    return {
        "message": "مرحباً بك في واجهة برمجة نظام الإجابة على الأسئلة",
        "message_en": "Welcome to the Youm7 QA API",
        "version": "1.0.0",
        "endpoints": {
            "ask": "POST /ask",
            "search": "POST /search",
            "health": "GET /health",
            "docs": "GET /docs",
        },
    }


@app.get(
    "/health",
    summary="Service health check",
    response_description="Loaded-resources status and counts",
)
def health():
    """Report whether model + index are loaded and how much corpus is indexed."""
    return {
        "status": "healthy",
        "model_loaded": app.state.model is not None,
        "index_loaded": app.state.index is not None,
        "total_chunks": app.state.total_chunks,
        "total_articles": app.state.total_articles,
        "model_name": app.state.model_name,
    }


@app.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a question and get an extracted answer",
    response_description="Formatted answer with confidence and source citation",
)
def ask_endpoint(req: AskRequest):
    """Validate the question, run the QA pipeline, return the final answer dict."""
    t0 = time.time()
    q = (req.question or "").strip()

    if not q:
        raise HTTPException(status_code=400, detail="السؤال لا يمكن أن يكون فارغاً")
    if len(q) < 5:
        raise HTTPException(status_code=400, detail="السؤال قصير جداً (5 أحرف على الأقل)")
    if len(q) > 500:
        raise HTTPException(status_code=400, detail="السؤال طويل جداً (500 حرف كحد أقصى)")

    try:
        result = ask(
            q,
            top_k=req.top_k,
            model=app.state.model,
            index=app.state.index,
            metadata=app.state.metadata,
        )
    except Exception:
        logger.exception("ask() failed for question: %r", q)
        raise HTTPException(status_code=500, detail="حدث خطأ في معالجة السؤال")

    result["processing_time_ms"] = int((time.time() - t0) * 1000)
    return result


@app.post(
    "/search",
    response_model=SearchResponse,
    summary="Raw retrieval — chunks without answer extraction",
    response_description="Top-k matching chunks with scores and previews",
)
def search_endpoint(req: SearchRequest):
    """Run FAISS retrieval and return the raw chunks (no threshold, no extraction)."""
    q = (req.query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="الاستعلام لا يمكن أن يكون فارغاً")

    try:
        results = retrieve(
            q,
            top_k=req.top_k,
            apply_threshold=False,
            model=app.state.model,
            index=app.state.index,
            metadata=app.state.metadata,
        )
    except Exception:
        logger.exception("retrieve() failed for query: %r", q)
        raise HTTPException(status_code=500, detail="حدث خطأ في معالجة الاستعلام")

    items = [
        {
            "rank": r["rank"],
            "score": round(float(r["score"]), 4),
            "title": r["title"],
            "category": r["category"],
            "url": r["url"],
            "chunk_preview": (r["chunk_text"] or "")[:200],
            "chunk_index": int(r["chunk_index"]),
        }
        for r in results
    ]
    return {"query": q, "total_results": len(items), "results": items}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    print("╔══════════════════════════════════════════════════════╗")
    print("║  Youm7 QA API — Starting...                          ║")
    print("║  Swagger docs : http://localhost:8000/docs           ║")
    print("║  Health check : http://localhost:8000/health         ║")
    print("║  Ask a question: POST http://localhost:8000/ask      ║")
    print("╚══════════════════════════════════════════════════════╝")

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
