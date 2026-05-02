# Youm7 QA — API Documentation

**Arabic Question Answering REST API over the اليوم السابع corpus.**

This document describes the four HTTP endpoints exposed by `api.py`, their
request/response schemas, error codes, and integration examples in
Python, JavaScript, and HTML.

---

## Overview

| Property | Value |
|---|---|
| **Base URL** | `http://localhost:8000` |
| **Format** | JSON over HTTP/1.1 |
| **Authentication** | None required (educational deployment) |
| **Content-Type** | `application/json` for both request and response |
| **Language** | Arabic content; all error messages and labels in Arabic |
| **CORS** | `*` for `GET, POST` — any frontend origin is allowed |
| **Stateless** | Yes — every request is independent |
| **Concurrency** | Safe — model and index are loaded once at startup, reused on every request |
| **Average latency** | 14–60 ms per `/ask` once the model is in memory |

The model used internally is `paraphrase-multilingual-MiniLM-L12-v2` (a
sentence-transformer producing 384-dim L2-normalized vectors). The FAISS
index is `IndexFlatIP`, so inner-product equals cosine similarity for
these embeddings.

---

## Quick Start

```bash
# 1. Start the server (must have completed Stages 1–4 first)
python api.py

# 2. Hit the welcome endpoint
curl http://localhost:8000/

# 3. Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  --data-binary '{"question":"ما هو سعر الذهب اليوم؟","top_k":5}'
```

> **Windows tip:** the cmd.exe / PowerShell `curl` re-encodes Arabic in
> request bodies to cp1252, turning the question into `?` characters
> before it leaves your machine. Either save the JSON body to a UTF-8 file
> and pass `--data-binary @body.json`, or use Python `requests` (which is
> UTF-8 by default), or use the included Swagger UI at `/docs`.

---

## Endpoints

There are four endpoints. They are summarized in the table below and then
each is documented in detail.

| # | Method | Path       | Purpose                                          |
|---|--------|------------|--------------------------------------------------|
| 1 | GET    | `/`        | Welcome message + endpoint index                 |
| 2 | GET    | `/health`  | Health check + system stats                      |
| 3 | POST   | `/ask`     | Full QA: retrieve → extract → format             |
| 4 | POST   | `/search`  | Raw FAISS retrieval (no answer extraction)       |

The interactive Swagger UI is auto-mounted at `/docs` and a ReDoc page at
`/redoc`.

---

### 1. `GET /`

**Description (English)**
Returns a welcome payload and the list of all available endpoints. Useful
as a smoke test that the server is alive and reachable.

**الوصف بالعربية**
يرجع رسالة ترحيب وقائمة بجميع نقاط النهاية المتاحة. مفيدة كاختبار سريع
للتأكد من أن الخادم يعمل.

**Request body** — none.

**Response fields**

| Field        | Type   | Description                                       |
|--------------|--------|---------------------------------------------------|
| `message`    | string | Welcome message in Arabic                         |
| `message_en` | string | Welcome message in English                        |
| `version`    | string | API version (`"1.0.0"`)                           |
| `endpoints`  | object | Map of endpoint name → method/path                |

**Example request (curl)**

```bash
curl http://localhost:8000/
```

**Example request (Python)**

```python
import requests
resp = requests.get("http://localhost:8000/")
print(resp.json())
```

**Example response (200 OK)**

```json
{
  "message": "مرحباً بك في واجهة برمجة نظام الإجابة على الأسئلة",
  "message_en": "Welcome to the Youm7 QA API",
  "version": "1.0.0",
  "endpoints": {
    "ask": "POST /ask",
    "search": "POST /search",
    "health": "GET /health",
    "docs": "GET /docs"
  }
}
```

---

### 2. `GET /health`

**Description (English)**
Reports whether the model and FAISS index are loaded, how much corpus is
indexed, and which embedding model is active. Designed for monitoring
probes — there is no rate limit.

**الوصف بالعربية**
يكشف ما إذا كان النموذج وفهرس FAISS محمّلَين، وعدد المقاطع والمقالات،
واسم النموذج المستخدم. مخصص لاختبارات المراقبة.

**Request body** — none.

**Response fields**

| Field             | Type    | Description                                       |
|-------------------|---------|---------------------------------------------------|
| `status`          | string  | Always `"healthy"` if the server can respond      |
| `model_loaded`    | boolean | True if the sentence-transformer was loaded       |
| `index_loaded`    | boolean | True if the FAISS index was loaded                |
| `total_chunks`    | int     | Number of vectors in the FAISS index              |
| `total_articles`  | int     | Number of distinct source documents               |
| `model_name`      | string  | The sentence-transformer model name               |

**Example request (curl)**

```bash
curl http://localhost:8000/health
```

**Example response (200 OK)**

```json
{
  "status": "healthy",
  "model_loaded": true,
  "index_loaded": true,
  "total_chunks": 62,
  "total_articles": 30,
  "model_name": "paraphrase-multilingual-MiniLM-L12-v2"
}
```

---

### 3. `POST /ask`

**Description (English)**
The primary QA endpoint. Embeds the question, retrieves the top-k chunks
by cosine similarity, applies a confidence gate (best score must be
≥ 0.30), takes the top chunk and selects the two sentences whose
keyword-overlap with the question is highest, then returns the formatted
answer with a confidence label and source citation.

**الوصف بالعربية**
نقطة النهاية الرئيسية للإجابة عن الأسئلة. تستقبل سؤالاً بالعربية، تحوّله إلى
متجه دلالي، تبحث في الفهرس، تستخرج جملتين من القطعة الأعلى تطابقاً، ثم
ترجع الإجابة مع درجة ثقة ومصدر مرجعي وحتى ٣ مقالات ذات صلة.

**Request body**

| Field      | Type   | Required | Default | Description                                            |
|------------|--------|----------|---------|--------------------------------------------------------|
| `question` | string | yes      | —       | The question, in Arabic. 5–500 characters.             |
| `top_k`    | int    | no       | `5`     | Number of chunks to retrieve, before extraction. 1–10. |

**Response fields**

| Field                | Type             | Description                                                                          |
|----------------------|------------------|--------------------------------------------------------------------------------------|
| `question`           | string           | The original question, echoed back                                                   |
| `answer`             | string           | The extracted Arabic answer (top 2 sentences from the best chunk)                    |
| `confidence`         | float            | Cosine score of the top chunk, rounded to 2 decimals (`0.00` – `1.00`)               |
| `confidence_label`   | string           | One of `"عالية"` (≥0.65), `"متوسطة"` (≥0.40), `"منخفضة"` (≥0.30), `"لا توجد نتائج"` |
| `source_title`       | string           | Title of the cited article                                                           |
| `source_url`         | string           | URL of the cited article                                                             |
| `source_category`    | string           | One of `"سياسة"`, `"اقتصاد"`, `"رياضة"`, `"تكنولوجيا"`, `"صحة"`                  |
| `related_sources`    | array of objects | Up to 3 related sources with `title`, `url`, `score`, `category`                     |
| `scraped_at`         | string           | UTC timestamp of when the source was scraped (ISO-8601 with `Z`)                    |
| `processing_time_ms` | int              | Server-side time from request received to response ready, in milliseconds            |

**Example request (curl)**

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  --data-binary '{"question":"ما هو سعر الذهب اليوم؟","top_k":5}'
```

**Example request (Python)**

```python
import requests

resp = requests.post(
    "http://localhost:8000/ask",
    json={"question": "ما هو سعر الذهب اليوم؟", "top_k": 5},
)
data = resp.json()
print(data["answer"])
print(data["confidence_label"], f"({data['confidence']:.2f})")
print("Source:", data["source_url"])
```

**Example response (200 OK)**

```json
{
  "question": "ما هو سعر الذهب عيار 21 في مصر اليوم؟",
  "answer": "استقر سعر الذهب عيار 24 اليوم في مصر خلال تعاملات السبت 2 مايو 2026 عند مستوى 7960 جنيه، حيث عادت الاونصه للتداول اعلى مستوى 4600 دولار بعد ملامسه ادنى مستوى خلال الجلسه ويعد عيار 24 الاكثر نقاء بين الاعيره المختلفه",
  "confidence": 0.9,
  "confidence_label": "عالية",
  "source_title": "سعر الذهب عيار 24 اليوم فى مصر السبت 2 مايو 2026 يسجل 7960 جنيها",
  "source_url": "https://www.youm7.com/story/2026/5/2/سعر-الذهب-عيار-24-اليوم-فى-مصر-السبت-2-مايو/7398505",
  "source_category": "اقتصاد",
  "related_sources": [
    {
      "title": "الذهب يتراجع فى مصر اليوم.. ماذا يحدث بالسوق؟",
      "url": "https://www.youm7.com/story/2026/5/1/الذهب-يتراجع-فى-مصر-اليوم-ماذا-يحدث-بالسوق/7398390",
      "score": 0.8083,
      "category": "اقتصاد"
    },
    {
      "title": "الذهب يتراجع فى مصر اليوم.. ماذا يحدث بالسوق؟",
      "url": "https://www.youm7.com/story/2026/5/1/الذهب-يتراجع-فى-مصر-اليوم-ماذا-يحدث-بالسوق/7398390",
      "score": 0.7438,
      "category": "اقتصاد"
    }
  ],
  "scraped_at": "2026-05-02T04:17:13Z",
  "processing_time_ms": 14
}
```

**No-answer response (still HTTP 200)**

When the best retrieved score is below the confidence threshold (`0.30`),
the API returns:

```json
{
  "question": "ما هي عاصمة كوكب المريخ؟",
  "answer": "عذراً، لا تتوفر معلومات كافية للإجابة على هذا السؤال",
  "confidence": 0.0,
  "confidence_label": "لا توجد نتائج",
  "source_title": "",
  "source_url": "",
  "source_category": "",
  "related_sources": [],
  "scraped_at": "",
  "processing_time_ms": 12
}
```

This is **not** an error — it is the expected behavior for off-topic
questions; clients should branch on `confidence_label`.

**Error responses**

| HTTP Code | Arabic Message                              | Cause                                       |
|-----------|---------------------------------------------|---------------------------------------------|
| `400`     | `السؤال لا يمكن أن يكون فارغاً`              | `question` is empty or whitespace-only      |
| `400`     | `السؤال قصير جداً (5 أحرف على الأقل)`        | `question` shorter than 5 characters        |
| `400`     | `السؤال طويل جداً (500 حرف كحد أقصى)`        | `question` longer than 500 characters       |
| `422`     | (Pydantic validation error JSON)            | `top_k` outside `1–10`, missing field, etc. |
| `500`     | `حدث خطأ في معالجة السؤال`                  | Internal pipeline failure                   |

---

### 4. `POST /search`

**Description (English)**
Raw FAISS retrieval — returns the top-k chunks ranked by cosine
similarity, **without** sentence extraction and **without** the
confidence threshold. Useful for debugging retrieval quality, building a
reranker on top, or browsing the corpus.

**الوصف بالعربية**
نقطة بحث مباشرة — تُرجع أفضل k قطعة بحسب التشابه الجيب التمام، دون
استخراج الإجابة ودون تطبيق حد الثقة. مفيدة للتصحيح وفهم جودة الاسترجاع.

**Request body**

| Field   | Type   | Required | Default | Description                                  |
|---------|--------|----------|---------|----------------------------------------------|
| `query` | string | yes      | —       | Free-text query in Arabic.                   |
| `top_k` | int    | no       | `3`     | Number of chunks to return. 1–10.            |

**Response fields**

| Field           | Type             | Description                                          |
|-----------------|------------------|------------------------------------------------------|
| `query`         | string           | Echoed query                                         |
| `total_results` | int              | Number of items in `results`                         |
| `results`       | array of objects | See below                                            |

Each item in `results`:

| Field           | Type   | Description                                                |
|-----------------|--------|------------------------------------------------------------|
| `rank`          | int    | 1-based rank (1 = best match)                              |
| `score`         | float  | Cosine score, rounded to 4 decimals                        |
| `title`         | string | Article title                                              |
| `category`      | string | Section category                                           |
| `url`           | string | Article URL                                                |
| `chunk_preview` | string | First 200 characters of the chunk text                     |
| `chunk_index`   | int    | Position of this chunk inside its source document          |

**Example request (curl)**

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  --data-binary '{"query":"الذهب في مصر","top_k":3}'
```

**Example request (Python)**

```python
import requests
resp = requests.post(
    "http://localhost:8000/search",
    json={"query": "الذهب في مصر", "top_k": 3},
)
for r in resp.json()["results"]:
    print(f"{r['rank']:>2}. [{r['score']:.3f}] {r['title']}")
```

**Example response (200 OK)**

```json
{
  "query": "الذهب في مصر",
  "total_results": 3,
  "results": [
    {
      "rank": 1,
      "score": 0.7574,
      "title": "سعر الذهب عيار 24 اليوم فى مصر السبت 2 مايو 2026 يسجل 7960 جنيها",
      "category": "اقتصاد",
      "url": "https://www.youm7.com/story/2026/5/2/سعر-الذهب-عيار-24-اليوم-فى-مصر-السبت-2-مايو/7398505",
      "chunk_preview": "استقر سعر الذهب عيار 24 اليوم في مصر خلال تعاملات السبت 2 مايو 2026 عند مستوى 7960 جنيه ...",
      "chunk_index": 0
    },
    {
      "rank": 2,
      "score": 0.7184,
      "title": "الذهب يتراجع فى مصر اليوم.. ماذا يحدث بالسوق؟",
      "category": "اقتصاد",
      "url": "https://www.youm7.com/story/2026/5/1/الذهب-يتراجع-فى-مصر-اليوم-ماذا-يحدث-بالسوق/7398390",
      "chunk_preview": "شهدت اسعار الذهب في مصر تراجعا خلال تعاملات اليوم الجمعه 1 مايو 2026 ...",
      "chunk_index": 0
    },
    {
      "rank": 3,
      "score": 0.6203,
      "title": "الذهب يتراجع فى مصر اليوم.. ماذا يحدث بالسوق؟",
      "category": "اقتصاد",
      "url": "https://www.youm7.com/story/2026/5/1/الذهب-يتراجع-فى-مصر-اليوم-ماذا-يحدث-بالسوق/7398390",
      "chunk_preview": "نحو ادوات ادخاريه بديله اكثر سيوله، وفقا لبيانات مجلس الذهب العالمي ...",
      "chunk_index": 1
    }
  ]
}
```

**Error responses**

| HTTP Code | Arabic Message                          | Cause                          |
|-----------|-----------------------------------------|--------------------------------|
| `400`     | `الاستعلام لا يمكن أن يكون فارغاً`        | `query` empty or whitespace    |
| `422`     | (Pydantic validation error JSON)        | `top_k` outside `1–10`         |
| `500`     | `حدث خطأ في معالجة الاستعلام`            | Internal pipeline failure      |

---

## Error Code Reference

The complete table of every error the server can emit:

| HTTP | Endpoint(s) | `detail` (Arabic)                           | Trigger                                                    |
|------|-------------|---------------------------------------------|------------------------------------------------------------|
| 400  | `/ask`      | السؤال لا يمكن أن يكون فارغاً                | `question` is empty or whitespace-only                     |
| 400  | `/ask`      | السؤال قصير جداً (5 أحرف على الأقل)          | `len(question.strip()) < 5`                                |
| 400  | `/ask`      | السؤال طويل جداً (500 حرف كحد أقصى)          | `len(question.strip()) > 500`                              |
| 400  | `/search`   | الاستعلام لا يمكن أن يكون فارغاً              | `query` empty or whitespace-only                           |
| 422  | both        | (Pydantic JSON, English)                     | `top_k` outside 1–10, missing required field, wrong type   |
| 500  | `/ask`      | حدث خطأ في معالجة السؤال                    | Internal exception (encoding error, FAISS error, etc.)     |
| 500  | `/search`   | حدث خطأ في معالجة الاستعلام                  | Same as above for the search path                          |

A "no answer found" outcome on `/ask` is **not** an error — it returns
HTTP 200 with the Arabic apology message in the `answer` field and empty
source fields.

---

## Integration Examples

### 1. Python script

```python
import requests

API = "http://localhost:8000"

def ask(question: str, top_k: int = 5) -> dict:
    """Call the QA API and return the answer dict."""
    r = requests.post(f"{API}/ask",
                      json={"question": question, "top_k": top_k},
                      timeout=10)
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    out = ask("ما هي أسباب أمراض القلب؟")
    print("Q:", out["question"])
    print("A:", out["answer"])
    print(f"Confidence: {out['confidence_label']} ({out['confidence']:.2f})")
    print("Source:", out["source_url"])
    for rs in out["related_sources"]:
        print(" -", rs["title"], f"(score {rs['score']:.3f})")
```

### 2. JavaScript (browser `fetch`)

```html
<script>
async function ask(question, topK = 5) {
  const resp = await fetch("http://localhost:8000/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK }),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

ask("ما هو سعر الذهب اليوم؟").then(data => {
  console.log(data.answer);
  console.log(`${data.confidence_label} (${data.confidence})`);
});
</script>
```

### 3. Plain HTML form

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<body>
  <h1>سؤال إلى Youm7 QA</h1>
  <form id="qa-form">
    <input type="text" id="q" placeholder="اكتب سؤالك..." size="50" />
    <button type="submit">اسأل</button>
  </form>
  <pre id="out"></pre>

  <script>
    document.getElementById("qa-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const q = document.getElementById("q").value.trim();
      const out = document.getElementById("out");
      out.textContent = "جارٍ التحميل...";
      try {
        const res = await fetch("http://localhost:8000/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: q }),
        });
        const data = await res.json();
        out.textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        out.textContent = "خطأ: " + err;
      }
    });
  </script>
</body>
</html>
```

### 4. Node.js (with `node-fetch` or built-in `fetch`)

```javascript
import fetch from "node-fetch"; // omit on Node 18+ where fetch is global

async function ask(question, topK = 5) {
  const r = await fetch("http://localhost:8000/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

const data = await ask("ما هي أحدث أخبار الذكاء الاصطناعي؟");
console.log(data.answer);
```

---

## Confidence Score Semantics

| Label              | Score Range  | Recommended action                                                   |
|--------------------|--------------|----------------------------------------------------------------------|
| **عالية**           | 0.65 – 1.00  | Display the answer prominently. Almost certainly correct.            |
| **متوسطة**          | 0.40 – 0.64  | Display with a "may be partial" caveat or show top 2 chunks.         |
| **منخفضة**          | 0.30 – 0.39  | Display with a clear warning, or hide and offer "see related" instead. |
| **لا توجد نتائج**   | < 0.30       | Show the apology message; the system refuses to guess.               |

The confidence score is **cosine similarity** of the L2-normalized
question vector against the L2-normalized chunk vector. It is bounded
in `[-1, 1]` mathematically, but for this Arabic news corpus and model
it falls almost entirely in `[0, 1]`.

---

## CORS

The server enables permissive CORS by default so any browser-based
frontend can call it during development:

- `allow_origins=["*"]`
- `allow_methods=["GET", "POST"]`
- `allow_headers=["*"]`

If you deploy this to a public host, **restrict `allow_origins` to your
frontend's domain**. See `api.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],   # ← change this
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

## Performance Notes

| Phase                 | Cold start | Warm |
|-----------------------|-----------:|-----:|
| Model load (Stage 5)  | 5–10 s     | —    |
| FAISS index load      | <100 ms    | —    |
| Per-question encoding | ~10 ms     | ~10 ms |
| FAISS top-5 search    | <1 ms      | <1 ms |
| Sentence extraction   | ~1 ms      | ~1 ms |
| **End-to-end `/ask`** | **5–10 s** (first request) | **14–60 ms** (subsequent) |

The dominant cost on a cold request is loading the model from the
HuggingFace cache. After the first request, each subsequent question
returns in tens of milliseconds.

---

## Versioning

Current API version: **`1.0.0`**.

| Version | Changes |
|---------|---------|
| 1.0.0   | Initial release. 4 endpoints: `/`, `/health`, `/ask`, `/search`. |

Future breaking changes will bump the major version (`2.0.0`) and the API
will be reachable at `/v2/...`.

---

## Support / Issues

This is an academic project. If something breaks:

1. Verify the server printed `✅ Youm7 QA API is ready` on startup.
2. `curl http://localhost:8000/health` and check `model_loaded` and
   `index_loaded` are both `true`.
3. If they are `false`, run **all** of `youm7_scraper.py` →
   `preprocess.py` → `embed.py` first to regenerate the indexed corpus.
4. Read the server's terminal log — every request is logged with method,
   path, status, and latency in milliseconds.

---

*— End of API Documentation —*
