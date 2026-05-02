# Website Question Answering System for Arabic News
## نظام الإجابة على الأسئلة من المواقع الإخبارية العربية

**A semantic retrieval-and-extraction pipeline over the اليوم السابع corpus.**

| Field | Value |
|---|---|
| Author | \<mohamed sabry\> |
| University | \<Ejust\> |
| Course | Natural Language Processing |
| Date | May 2026 |


---

## Abstract

### العربية

في عالم الأخبار الرقمية يصدر يومياً آلاف المقالات بالعربية، يجد القارئ
صعوبة في الوصول إلى معلومة محددة بداخلها. يقدّم هذا العمل نظاماً مفتوح
المصدر للإجابة عن الأسئلة باللغة العربية بعد بنائه على خمس مراحل
متعاقبة. في الأولى، تم استخدام Selenium مع BeautifulSoup لجمع ٣٠ مقالاً
من خمسة أقسام في موقع *اليوم السابع* (السياسة، الاقتصاد، الرياضة،
التكنولوجيا، الصحة) مع تطبيق ست تقنيات لتجاوز الحظر. في الثانية، طُبقت
خطوات تنظيف وتطبيع للنصوص العربية باستخدام مكتبة `pyarabic`، ثم قُسّمت
إلى ٦٢ مقطعاً متداخلاً (٢٠٠ كلمة لكل مقطع، تداخل ٥٠ كلمة). في الثالثة،
حُوِّلت المقاطع إلى متجهات بأبعاد ٣٨٤ باستخدام نموذج
`paraphrase-multilingual-MiniLM-L12-v2`، وفُهرست في FAISS مع تشابه جيب
التمام. في الرابعة، صُمم خوارزم استخراجي يختار جملتين من أعلى مقطع
تطابقاً مع كلمات السؤال. في الخامسة، نُشر النظام عبر FastAPI بأربع نقاط
نهاية وواجهة عربية كاملة. على خمسة أسئلة اختبارية، حقق النظام درجة
*عالية* في ثلاثة منها (٠٫٦٥–٠٫٩٠) و*متوسطة* في اثنين، وكانت الحالات
المتوسطة ناتجة عن عدم توفر مقالات كافية في المدونة لا عن أخطاء استرجاع.
يُظهر العمل أن نموذج تضمين متعدد اللغات جاهز ومفهرس FAISS بسيط يكفيان
لبناء نظام عربي عملي للإجابة عن الأسئلة بدون أي تدريب أو ضبط مسبق.

### English

In a digital news landscape that produces thousands of Arabic articles
per day, finding a specific piece of information inside any one article
is hard. This paper presents an end-to-end Arabic question-answering
system built in five stages over the *Youm7* corpus. **Stage 1** scrapes
30 articles from five sections (politics, economy, sports, technology,
health) using Selenium and BeautifulSoup, with six anti-blocking
techniques. **Stage 2** applies Arabic-aware cleaning with the
`pyarabic` library — Alef and Teh-Marbuta normalization, tashkeel and
tatweel stripping, URL/email removal — and splits each article into
overlapping 200-word chunks with 50-word overlap, producing 62 chunks.
**Stage 3** encodes each chunk into a 384-dim vector with the
multilingual sentence-transformer
`paraphrase-multilingual-MiniLM-L12-v2` and stores them in a FAISS
`IndexFlatIP` so that inner-product equals cosine similarity on the
L2-normalized embeddings. **Stage 4** implements an extractive answer
generator that gates on a confidence threshold of 0.30 and selects the
two sentences in the top chunk with the highest keyword-overlap with the
question. **Stage 5** deploys the pipeline as a FastAPI service with
four endpoints and a vanilla-HTML/JS Arabic chatbot UI. Evaluation on
five test questions yielded three high-confidence answers (0.65–0.90)
and two medium-confidence answers (0.51 and 0.63); both medium cases
were corpus-coverage limitations, not retrieval failures. The system
demonstrates that competent Arabic QA is achievable with off-the-shelf
multilingual encoders, no fine-tuning, and a few hundred lines of
Python — given clean data and faithful preprocessing.

---

## 1. Introduction

### 1.1 Problem Statement

Arabic is the fourth-most-used language on the internet, but the
quantity of structured-search infrastructure available for Arabic
content lags far behind English. News portals like
*اليوم السابع* publish hundreds of articles per day in modern standard
Arabic, but a reader who wants to know — say — *ما هو سعر الذهب اليوم؟*
("what is the gold price today?") cannot ask the website that question.
They can only browse, scan headlines, and click through to articles
manually. Search bars on news sites typically perform keyword matching
against titles, which fails to surface partial-phrase questions and
synonym variations. The reader pays the cost of every additional click.

The challenge is intensified by Arabic's morphological richness: a
single word root (مثل: *كتب*) can produce dozens of inflected forms
(*يكتب، كاتب، مكتوب، كتابة...*). A keyword-based search for *كتاب* will
miss articles that only use *مكتوب*. Furthermore, Arabic exhibits
multiple orthographic variants of the same letter — most prominently
Alef (*أ، إ، آ، ا*) and Teh Marbuta (*ة، ه*) — that look identical to a
reader but are distinct Unicode codepoints, again confusing naive
search. A useful Arabic QA system must therefore embed text in a
semantic space where these variants collapse to the same neighbourhood.

### 1.2 Project Objectives

The project targets three concrete objectives:

1. **Automate Arabic article scraping** from a real, JavaScript-rendered
   news website while respecting anti-bot defenses. The scraper must be
   robust to dynamic content, rotating user agents, and the kind of
   intermittent rate-limiting that real news sites impose.
2. **Build a searchable vector index** that lets a question expressed in
   any Arabic phrasing find the most semantically related chunk in the
   corpus, regardless of surface-level orthographic differences.
3. **Answer questions in Arabic with a confidence score** that lets
   downstream applications (a chatbot, a search bar, a mobile app)
   decide whether to display, hedge, or refuse the answer.

A non-objective is *generative* QA: the system never invents text. Every
returned answer is a verbatim sentence from the indexed corpus, which
guarantees no hallucination at the cost of rejecting questions whose
answer is not literally in the corpus.

### 1.3 Scope

The corpus is restricted to the *اليوم السابع* (Youm7) website, and
specifically to the five flagship sections: politics (*سياسة*), economy
(*اقتصاد*), sports (*أخبار الرياضة*), technology (*علوم وتكنولوجيا*),
and health (*صحة وطب*). The system supports modern standard Arabic
(MSA); Egyptian dialect (*العامية المصرية*) questions are not in scope.
The pipeline is **extractive**, not generative: the answer is always a
quotation from the corpus.

---

## 2. Literature Review

Question-answering as a formal NLP task is several decades old. **IBM's
Watson** [1], which famously defeated the human champions of *Jeopardy!*
in 2011, popularized the architecture of (i) coarse retrieval, (ii)
fine-grained answer extraction, and (iii) candidate scoring and
reranking. Watson was a sprawling pipeline of hundreds of subsystems;
this project's architecture is a simplified, modern descendant of the
same three-step pattern.

The introduction of **BERT** [2] in 2019 reset the field. BERT
demonstrated that a single pre-trained transformer fine-tuned on the
**SQuAD** [3] reading-comprehension dataset could answer factoid
questions with super-human accuracy. The model treats QA as a span-
prediction task: given a passage and a question, predict the start and
end token offsets of the answer. The downside is that it requires a
fine-tuned model per language — and Arabic has historically been
under-resourced in this regard.

Arabic NLP introduces challenges absent from English. **AraBERT** [4]
addressed pre-training on Arabic text; **MARBERT** further specialized
on dialect data. Beyond model availability, Arabic is rich in
**morphological variants**: a noun can carry definite articles,
possessive suffixes, and case inflections all in one word; a verb can
encode subject, object, tense, mood, and voice in a single string. Add
to this the multiple **orthographic variants** of letters like Alef and
Teh Marbuta, and a faithful normalization step becomes essential before
any embedding model can produce stable similarity scores.

The shift from sparse retrieval (BM25, TF-IDF) to **dense retrieval**
was accelerated by **Sentence-BERT** [5] in 2019, which fine-tuned BERT
with a siamese architecture to produce sentence embeddings whose cosine
distance matched semantic similarity. This unlocked the modern pattern
of *embedding chunk + nearest-neighbour search* used in this project.
Multilingual variants of Sentence-BERT (such as the
`paraphrase-multilingual-MiniLM-L12-v2` model used here) extend the
embedding space to over 50 languages including Arabic, all without
language-specific fine-tuning.

The retrieval step itself was made tractable at scale by **FAISS**
(Facebook AI Similarity Search) [6], which provides a family of indexes
that trade off recall for speed. For a corpus of only 62 vectors, an
exhaustive index (`IndexFlatIP`) is both faster and more accurate than
the approximate ones; the choice scales linearly and would still be
sub-millisecond at hundreds of thousands of vectors.

A more recent paradigm is **Retrieval-Augmented Generation (RAG)** [7],
in which a retriever fetches relevant context and a generator (LLM)
composes a fluent answer that may *paraphrase* the retrieved content.
RAG is more powerful than extractive QA but has two costs: it requires
a hosted LLM (with API keys, latency, and per-token billing) and it
introduces hallucination risk. This project explicitly chose the
extractive variant for both pedagogical and integrity reasons. The
**ARCD** Arabic Reading Comprehension Dataset [8] and Google's TyDi QA
[9] are the principal Arabic benchmarks; a future iteration of this
project could fine-tune AraBERT on ARCD to add a generative variant.

---

## 3. Methodology

### 3.1 System Architecture

```
  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
  │  Stage 1    │    │   Stage 2    │    │   Stage 3   │
  │  Scraping   │───▶│Preprocessing │───▶│  Embedding  │
  │ Selenium+BS │    │  pyarabic    │    │   FAISS     │
  │ 30 articles │    │  62 chunks   │    │ 384-dim vec │
  └─────────────┘    └──────────────┘    └─────────────┘
                                                │
        ┌───────────────────────────────────────┘
        ▼
  ┌─────────────┐    ┌──────────────┐
  │  Stage 4    │    │   Stage 5    │
  │   Answer    │───▶│  Deployment  │
  │ Generation  │    │   FastAPI    │
  │  Extractive │    │  index.html  │
  └─────────────┘    └──────────────┘
```

Each box is implemented in a single Python file
(`youm7_scraper.py`, `preprocess.py`, `embed.py`, `answer.py`,
`api.py`). Stages communicate exclusively through versioned files in
the `output/` directory, which makes the pipeline reproducible and
debuggable: any stage can be re-run without redoing the previous ones,
as long as its input file exists.

### 3.2 Data Collection

The target website is **اليوم السابع** at `https://www.youm7.com`.
Five seed URLs were used, one per section, of the form
`https://www.youm7.com/Section/<slug>/<id>/1` — for example
`https://www.youm7.com/Section/سياسة/319/1` for politics. The site uses
JavaScript-rendered article cards, so a simple HTTP GET returns an HTML
shell with no `<a>` tags inside the section grids. We therefore use
**Selenium** with headless Chrome — orchestrated via
`webdriver-manager` to auto-fetch the matching ChromeDriver — and parse
the post-render DOM with **BeautifulSoup** + `lxml`.

Six **anti-blocking** techniques are applied:

1. **User-Agent rotation** across six realistic strings (Chrome
   Windows/macOS/Android, Firefox, Safari, Edge), refreshed per
   navigation via the Chrome DevTools Protocol command
   `Network.setUserAgentOverride`.
2. **Persistent session** — a single Chrome instance is reused across
   the whole run so cookies persist, mimicking a real browser session.
3. **Homepage warmup** — every run begins with a `GET /` to the
   homepage so the site sees a normal browsing pattern before the
   per-article requests begin.
4. **Random delays** of 1.5–3.0 seconds between requests, drawn from a
   uniform distribution.
5. **Referer header** set to the homepage on every article navigation,
   refreshed alongside the User-Agent via `Network.setExtraHTTPHeaders`.
6. **Full Arabic-browser header set**: `Accept-Language: ar,ar-EG;q=0.9,en;q=0.8`,
   `Accept-Encoding: gzip, deflate, br`, plus `Connection: keep-alive`,
   `Upgrade-Insecure-Requests: 1`, and `Cache-Control: max-age=0`.

The scraper additionally implements a per-seed cap (6 articles per
section) to ensure all five categories are represented inside the
global cap of 30 articles, and a content-based **block detection**
(matching `Access Denied`, `captcha`, `Just a moment`) that rejects
soft-block pages even when they return HTTP 200.

After collection, articles are cleaned page-by-page: 12 layout tags
(`<script>`, `<style>`, `<nav>`, `<header>`, `<footer>`, `<aside>`,
`<form>`, `<button>`, `<svg>`, `<canvas>`, `<iframe>`, `<noscript>`) are
decomposed wholesale, and any element whose `class` or `id` contains
`ad`, `banner`, `social`, `share`, `sidebar`, `comment`, etc. is
removed. The body is then extracted from `#articleBody`, `<p>` and
heading tags are concatenated, fragments shorter than 40 characters are
discarded, and any page whose final body is shorter than 150 characters
is skipped.

The result of Stage 1 is `output/youm7_corpus.json`: 30 articles, 11,179
words, ~66,000 characters, with full UTF-8 Arabic text and per-article
metadata (URL, title, section category, scrape timestamp).

### 3.3 Preprocessing

Stage 2 prepares the corpus for embedding. The `pyarabic` library
provides battle-tested implementations of the standard Arabic
normalizations.

**Hamza / Alef normalization (أ، إ، آ، ٱ → ا).**
The same word can be written with a hamza-above-alef (*أصدر*), a
hamza-below-alef (*إصدار*), an alef-with-madda (*آلية*), or a plain
alef (*استمر*). All four variants are valid in MSA but they are
distinct Unicode codepoints, which means a naive substring search for
*استمر* would miss *إستمر*. The normalization collapses all four
variants to a plain alef (*ا*).

**Teh Marbuta normalization (ة → ه).**
The Teh Marbuta is the feminine ending in Arabic and is a separate
codepoint from the regular *ه*. In handwriting and informal Arabic
they look almost identical. Normalizing *ة* to *ه* increases the
recall of any matching algorithm, at the (negligible) cost of merging
a small number of distinct words.

**Tashkeel removal (ـَ ـِ ـُ ـّ → empty).**
Tashkeel are the diacritic marks that disambiguate vowels. Modern
Arabic text omits them in 99% of cases; when present, they break
naive matching. Stripping the Unicode block `U+064B – U+065F`
normalizes any text that does happen to include them. The example *كَتَبَ*
becomes *كتب*.

**Tatweel removal (ـ).**
Tatweel is a typographic stretch character that has no semantic value;
it is used to justify text. Stripping it is essential because *كـتـاب*
and *كتاب* must be considered the same word.

The text then passes through deterministic regular-expression filters
to remove URLs, email addresses, and any character that is not an
Arabic letter (`U+0600–U+06FF`), Latin letter (for brand names like
*iPhone*), digit (ASCII or Arabic-Indic `٠–٩`), whitespace, or one of
three allowed Arabic punctuation marks (*،*، *؟*، *؛*). All other
punctuation is removed; multiple consecutive whitespace characters are
collapsed to a single space.

**Chunking.**
Each cleaned article body is then split into overlapping word windows.
The chunk size is 200 words; the overlap is 50 words. Step size is
therefore 150 words. The motivation for **overlap** is that semantic
context can span chunk boundaries — a sentence that begins at word
197 of one chunk would otherwise be split between two chunks and
neither would contain its full context. With 50-word overlap, every
50-word stretch appears in two consecutive chunks (except the very
first and very last), guaranteeing that no sentence falls into a
boundary gap.

The result of Stage 2 is `output/youm7_chunks.json`: 62 chunk records,
each carrying full source metadata plus the cleaned `chunk_text`,
ready for embedding. A separate verification script
(`verify_preprocess.py`) runs 26 automated checks against this file
covering Arabic normalization, chunk overlap, encoding, and
metadata-vs-corpus consistency.

### 3.4 Model Selection

#### Why sentence-transformers over BERT QA?

Standard BERT QA (BERT fine-tuned on SQuAD) requires a *fine-tuned*
model per language and per task. There is no widely available
high-quality Arabic SQuAD-style fine-tuned model that fits the project's
computational budget (CPU-only, no GPU). Sentence-transformers, by
contrast, were pre-trained with a contrastive objective that makes them
useful **out of the box** for retrieval — no fine-tuning required.
This shifts the architecture from "BERT understands the question and
points to a span" to "embed both question and chunk, find the closest
chunk, then extract sentences from it" — much simpler and trainable on
zero data.

#### Why `paraphrase-multilingual-MiniLM-L12-v2`?

Among the multilingual sentence-transformers, this model was chosen
because:

1. **Native Arabic support.** It was trained on parallel data from over
   50 languages including Arabic; performance on Arabic semantic
   similarity tasks is competitive with much larger models.
2. **Lightweight.** ~120 MB on disk, runs on CPU at ~10 ms per query.
   Larger models (`mpnet-base-v2`, multilingual XLM-R variants) are
   2–4× larger and 2–3× slower without measurable improvement on this
   short-news-article corpus.
3. **384-dimensional output.** A reasonable trade-off between
   expressiveness and FAISS index footprint. 62 vectors × 384 floats =
   ~95 KB on disk.
4. **Free and self-hosted.** No API key required after the initial
   ~5-second download from HuggingFace.

#### Embedding process

For each chunk, the title and chunk text are concatenated
(*"{title} {chunk_text}"*) and passed to `model.encode(...)` with
`normalize_embeddings=True`. Concatenating the title gives the encoder
both the article-level context and the specific paragraph content,
which empirically improves retrieval. The result is a `(62, 384)`
NumPy array of float32 values, each row L2-normalized to length 1.

#### FAISS `IndexFlatIP` and why it equals cosine similarity

FAISS provides several index types; the simplest is `IndexFlatIP`,
which stores vectors verbatim and computes inner-product (dot product)
between the query and every stored vector. Because the embeddings are
L2-normalized, the inner product **equals** the cosine similarity:

  cos(a, b) = (a · b) / (‖a‖ × ‖b‖) = a · b   (when ‖a‖ = ‖b‖ = 1)

Using `IndexFlatIP` therefore gives exact cosine similarity without
the cost of recomputing norms at query time. With only 62 vectors, the
exhaustive search is instantaneous (sub-millisecond) and avoids the
recall loss of approximate-nearest-neighbour indexes.

### 3.5 Answer Generation

**Retrieval step.**
The user's question is encoded with the same model and the same
normalization. The resulting 384-dim vector is searched against the
FAISS index for the top-k (default 5) nearest chunks by inner product.
FAISS returns parallel arrays of scores and integer ids; the ids are
0-based positions into a metadata file that maps back to the original
chunk's URL, title, and full text.

**Confidence threshold (0.30).**
Before any answer is returned, the *top* score is compared against a
threshold of 0.30. If the best chunk in the corpus is less than 30%
similar to the question, the system refuses to answer with the
canonical message *"عذراً، لا تتوفر معلومات كافية للإجابة على هذا السؤال"*.
This threshold was chosen empirically: across the test set, all
genuinely-on-topic questions retrieved their target chunk at scores
above 0.50, while a control set of off-topic questions ("ما هي عاصمة
كوكب المريخ؟") produced top scores below 0.25.

**Sentence scoring.**
The text of the top chunk is split on `، . ؟ ؛ \n` into sentences. The
question is normalized identically to how the corpus was normalized,
then split into "keywords" (any word longer than 2 characters). Each
sentence in the chunk is scored as the count of keywords that appear
literally in the sentence. Because chunks were normalized in Stage 2,
a question word like *أمراض* is normalized to *امراض* before matching
against the chunk text, which itself contains *امراض*. Without this
normalization step, no question word would match anything.

**Extractive selection.**
The two sentences with the highest scores are selected, restored to
their original reading order, joined with the Arabic comma `، ` and
returned as the final answer. If no sentence scored above zero — i.e.
the question keywords don't literally appear in the chunk — the
system falls back to returning the first 200 characters of the chunk
as a sensible approximation.

**Confidence labelling.**
The same cosine score is mapped to a 4-bucket Arabic label:
*عالية* (≥0.65), *متوسطة* (≥0.40), *منخفضة* (≥0.30), or *لا توجد نتائج*
(<0.30). The thresholds were chosen so that an *عالية* answer
empirically corresponds to "the answer is in this chunk", while
*متوسطة* corresponds to "the answer is partially in this chunk".

### 3.6 Deployment

**FastAPI architecture.**
The service is implemented as a single FastAPI app in `api.py`. The
critical design decision is to load the embedding model, the FAISS
index, and the metadata **once** at startup using FastAPI's
**lifespan** event manager. They are stashed on `app.state` and reused
for every incoming request; the per-request cost is therefore the
~10 ms encoding plus sub-millisecond FAISS search, not the 5–10 s
model load.

**Endpoint design.**
Four endpoints are exposed:

- `GET /` — welcome and endpoint index, useful as a smoke test;
- `GET /health` — model and index loaded status, total chunks/articles,
  model name, all in JSON; designed for monitoring probes;
- `POST /ask` — the main QA endpoint with strict input validation
  (5–500 character question, top_k 1–10) and Arabic error messages
  using HTTP 400 for client errors;
- `POST /search` — raw retrieval that returns the top-k chunks
  without sentence extraction or confidence threshold; useful for
  debugging and reranking experiments.

The Pydantic v2 models `AskRequest`, `AskResponse`, `SearchRequest`,
`SearchResponse`, and `RelatedSource` give automatic OpenAPI
documentation at `/docs` (Swagger UI) and `/redoc`. CORS is
permissively enabled with `allow_origins=["*"]` to let any frontend
call the API during development.

**Frontend (`index.html`).**
A single-file HTML page with vanilla CSS and JavaScript implements a
fully RTL Arabic chatbot interface. It uses Google Fonts (Tajawal),
polls `/health` every 30 seconds for a status dot, offers two tabs
(QA and raw search), tracks the last 5 questions in `localStorage`,
shows a coloured confidence bar (green/yellow/red), and degrades
gracefully when the server is offline with the Arabic message
*"تعذر الاتصال بالخادم. تأكد من تشغيل api.py"*.

---

## 4. Results & Evaluation

### 4.1 Corpus Statistics

The 30 scraped articles were split evenly across the five sections (6
per section), producing a varying number of chunks per category
depending on each article's length:

| Category   | Articles | Chunks | Avg Words / Chunk |
|------------|---------:|-------:|------------------:|
| سياسة      |        6 |     13 |               172 |
| اقتصاد     |        6 |     13 |               171 |
| رياضة      |        6 |      8 |               158 |
| تكنولوجيا  |        6 |     12 |               181 |
| صحة         |        6 |     16 |               165 |
| **Total**  |   **30** | **62** |          **~169** |

Total corpus size: **11,179 words / 65,999 characters / 62 chunks**.
The technology section produced the longest chunks on average
because the scraped technology articles were the most verbose; the
sports section produced the fewest chunks because match-report
articles tend to be short.

### 4.2 QA Performance

Five test questions were used to probe each section. The retrieved
top score, the Arabic confidence label, and a manual judgment of
correctness are tabulated below:

| # | Question                                       | Top Score | Label    | Correct?     |
|---|------------------------------------------------|----------:|----------|--------------|
| 1 | ما هو سعر الذهب عيار 21 في مصر اليوم؟         |      0.90 | عالية     | ✅ Yes        |
| 2 | ما هي أسباب أمراض القلب؟                       |      0.82 | عالية     | ✅ Yes        |
| 3 | ما آخر أخبار الذكاء الاصطناعي وآبل؟            |      0.65 | عالية     | ✅ Yes        |
| 4 | ما هي مواعيد مباريات الدوري المصري؟            |      0.51 | متوسطة    | ⚠️ Partial   |
| 5 | ما هي نصائح لتقوية العضلات؟                   |      0.63 | متوسطة    | ⚠️ Partial   |

**3 of 5** answers were judged fully correct at "high" confidence;
**2 of 5** were partial.

### 4.3 Analysis

**Why the gold-price question worked perfectly (0.90).**
Q1 contains the literal token *الذهب*, which appears verbatim and
densely in the source article *"سعر الذهب عيار 24 اليوم فى مصر السبت 2 مايو 2026 يسجل 7960 جنيها"*.
The encoder sees a near-perfect lexical-and-semantic overlap. The
extractive sentence selector then easily picks the two sentences that
contain both *سعر* and *الذهب*, producing a fluent, factual answer
with the exact figure (7960 جنيه).

**Why the heart-disease question worked well (0.82).**
Q2 uses domain-specific terminology (*أعراض، أمراض، القلب*) that maps
directly onto the medical article *"أسباب وعوامل تزيد خطر أمراض القلب"*.
Specific medical terms have low ambiguity in the embedding space,
giving high cosine similarity. The first sentence of the article — a
definition of heart disease — was selected as the primary answer.

**Why the AI/Apple question worked at the threshold (0.65).**
Q3 mentions both *الذكاء الاصطناعي* and *آبل*, which jointly appear
in the source article *"الذكاء الاصطناعى يفاجئ آبل: طفرة غير متوقعة فى مبيعات أجهزة ماك"*.
This is the **borderline of high confidence** — exactly at 0.65 — and
is correct. With more AI articles in the corpus, this would likely
rise above 0.75.

**Why the fixtures question was partial (0.51).**
Q4 asks for the schedule of the Egyptian domestic league
(*الدوري المصري*). The scraped sports section happens to contain
articles about the Egyptian *national team* preparing for the 2026
World Cup, plus articles about ALagne sports league referee
appointments — but no article that *lists* league fixtures. The
system surfaces the closest substitute (*"موعد مباراة منتخب مصر وروسيا الودية"*)
at 0.51 — a valid medium-confidence pointer to a related-but-not-target
article. This is a corpus-coverage failure, not a retrieval failure.

**Why the muscle-training question was partial (0.63).**
Similarly, Q5 asks for advice on muscle strengthening
(*نصائح لتقوية العضلات*). The corpus contains an article about
*أنواع المشروبات الغنية بالبروتين لتقوية العضلات* (protein drinks for
muscle building) and another about metabolism. The system surfaces a
single sentence about muscle building from the metabolism article at
score 0.63 — again a medium-confidence partial answer reflecting
corpus depth, not algorithmic error.

The clear pattern is that **retrieval scores correctly predict answer
quality**: the three high-confidence answers were judged correct, and
the two medium-confidence answers were judged partial. The confidence
score is therefore a useful gate for downstream applications.

---

## 5. Limitations

### 5.1 Small corpus (30 articles, 62 chunks)

**What.** The corpus is bounded at 30 articles, producing 62 chunks
totalling ~11K words.
**Why.** A per-section cap of 6 articles in the scraper, plus a global
cap of 30, was set to keep the demonstration tractable and to ensure
balanced category representation.
**How to fix.** Raise `MAX_ARTICLES` in `youm7_scraper.py`. A larger
corpus (~500 articles) would directly raise the average confidence on
borderline questions like Q4 and Q5. A daily cron job that adds the
day's articles incrementally would keep the index always-fresh.

### 5.2 Extractive only — no synthesis

**What.** Every answer is a verbatim quotation. Questions whose answer
requires combining facts from multiple chunks always lose information.
**Why.** Project specification chose this for safety and pedagogy: an
extractive system cannot hallucinate.
**How to fix.** Add a `/generate` endpoint backed by a hosted LLM
(Claude, GPT-4) that receives the top 3 chunks as context and generates
a fluent paraphrase. Keep the extractive path as the safe default and
let clients opt into generation.

### 5.3 MSA-only matching

**What.** Egyptian-dialect questions like *"بكام الدهب النهارده؟"*
fail to match MSA articles even when semantically identical.
**Why.** The encoder is multilingual but trained predominantly on MSA;
the corpus is also MSA news.
**How to fix.** Add a query-rewriting step that maps dialect → MSA
using a small bilingual dictionary or a fine-tuned T5-Arabic
transliteration model. Alternatively, add MARBERT (which is trained
on dialect data) as a second embedder and ensemble the scores.

### 5.4 No answer caching

**What.** Every question hits the encoder and FAISS, even if the same
question was asked five seconds ago.
**Why.** Caching wasn't a project requirement and per-request cost is
already only 14–60 ms.
**How to fix.** Add a Redis layer keyed by the normalized question
with a TTL of ~1 hour. Frequent questions (e.g. "what's the gold price
today?") would then return in <1 ms.

### 5.5 Single source

**What.** Only Youm7 is indexed; questions outside its coverage have
no answer source.
**Why.** Project scope.
**How to fix.** Add additional scrapers in a `sources/` package
(*المصري اليوم*، *الأهرام*، *Cairo Scene* for English) and a `site`
field in the metadata; let `/ask` filter or weight by `site`.

### 5.6 No question spell correction

**What.** A question with a typo (*ما هو سار الذهب اليوم؟*) gets a
weaker match because the typo word doesn't normalize to anything in
the corpus vocabulary.
**Why.** Out of scope.
**How to fix.** Pre-process the question with `pyspellchecker` or a
fine-tuned Arabic typo corrector before encoding. A single-pass
correction at query time is essentially free.

### 5.7 JS-rendered scraping is slow

**What.** Each article requires a full Chrome page load (~5–8 s),
making a 30-article scrape take ~3–4 minutes.
**Why.** The site renders article cards via JavaScript; a simple HTTP
GET returns an empty shell.
**How to fix.** Cache rendered HTML to disk so re-runs only re-fetch
modified pages. Switch to Playwright with a persistent browser
context, which keeps Chrome warm between articles and cuts ~1 s per
article. For maintenance scrapes (already-known URLs), use the
site's structured-data endpoints if any.

---

## 6. Future Work

1. **Scale the corpus to 500+ articles** with a daily refresh job. The
   current 30-article cap exists only for demonstration; the pipeline
   itself scales linearly to tens of thousands of chunks before FAISS
   would need to switch from `IndexFlatIP` to `IndexHNSW`.
2. **Fine-tune AraBERT on the ARCD Arabic Reading Comprehension
   Dataset.** This would add a true span-prediction model that could
   replace the keyword-overlap sentence selector with a learned span
   predictor, plausibly improving extraction quality on long chunks.
3. **Add Retrieval-Augmented Generation** with an LLM backend so the
   system can synthesize answers across multiple chunks. The
   confidence threshold would gate generation, ensuring the LLM is
   only invoked when the corpus actually contains relevant material.
4. **Support Egyptian Arabic dialect.** Add a query-rewriting step
   and/or a dialect-trained second encoder; ensemble the two scores.
5. **Add a Redis cache** for frequently-asked questions, keyed by
   normalized question text, with a 1-hour TTL.
6. **Deploy to a cloud host** — AWS Lambda + API Gateway, Heroku, or a
   HuggingFace Space. The current image is small (~500 MB including
   the model weights) and runs comfortably on a 1-CPU VM.
7. **Build a mobile app** (Flutter or React Native) that consumes the
   existing `/ask` endpoint. The API contract is stable.
8. **Expand to 10+ Egyptian news websites** — *المصري اليوم*،
   *الأهرام*، *البوابة*، *المصراوي*, etc. — with site-specific
   scrapers but a shared preprocessing and indexing pipeline. Add a
   `site` filter on the API so users can scope their questions.

---

## 7. Conclusion

This project built a complete Arabic question-answering system over a
real news website in five well-defined stages, from JS-rendered
scraping all the way to a polished web UI. The system demonstrates
that **competent Arabic QA is achievable today with off-the-shelf
multilingual encoders, no fine-tuning, and a few hundred lines of
Python**, provided the upstream data is cleaned and normalized
faithfully. The choice of an extractive architecture made the system
trustworthy by construction — every answer is a verbatim quotation
with a verifiable source link — and the cosine-similarity confidence
score correctly predicted answer quality on the test set, with all
three high-confidence answers judged correct and the two medium-
confidence answers correctly flagged as partial.

The path forward is straightforward: more data, a learned span
predictor on top of the current retriever, and an opt-in RAG mode for
multi-chunk synthesis. None of these changes require rewriting the
current pipeline — they slot in cleanly at the boundaries the five
stages already define. The same architecture, with a different scraper
and a different language model, would extend just as easily to French
news, Hebrew news, or any other under-resourced language. In a world
where Arabic content is plentiful but Arabic search is poor, even a
small, undergraduate-scale system like this one is a useful step.

---

## References

[1] Ferrucci, D. A. et al. (2010). *Building Watson: An Overview of the
DeepQA Project.* AI Magazine 31 (3): 59–79.

[2] Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K. (2019). *BERT:
Pre-training of Deep Bidirectional Transformers for Language
Understanding.* In Proceedings of NAACL-HLT 2019, pp. 4171–4186.

[3] Rajpurkar, P., Zhang, J., Lopyrev, K., & Liang, P. (2016). *SQuAD:
100,000+ Questions for Machine Comprehension of Text.* In Proceedings
of EMNLP 2016.

[4] Antoun, W., Baly, F., & Hajj, H. (2020). *AraBERT: Transformer-
Based Model for Arabic Language Understanding.* In Proceedings of
the 4th Workshop on Open-Source Arabic Corpora and Processing Tools
(LREC 2020), pp. 9–15.

[5] Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: Sentence
Embeddings using Siamese BERT-Networks.* In Proceedings of EMNLP-
IJCNLP 2019, pp. 3982–3992.

[6] Johnson, J., Douze, M., & Jégou, H. (2021). *Billion-Scale
Similarity Search with GPUs.* IEEE Transactions on Big Data 7 (3):
535–547.

[7] Lewis, P. et al. (2020). *Retrieval-Augmented Generation for
Knowledge-Intensive NLP Tasks.* In Advances in Neural Information
Processing Systems 33 (NeurIPS 2020), pp. 9459–9474.

[8] Mozannar, H., Hajal, K. E., Maamary, E., & Hajj, H. (2019).
*Neural Arabic Question Answering.* In Proceedings of the Fourth
Arabic Natural Language Processing Workshop (ACL 2019), pp. 108–118.

[9] Clark, J. H. et al. (2020). *TyDi QA: A Benchmark for Information-
Seeking Question Answering in Typologically Diverse Languages.*
Transactions of the ACL 8: 454–470.

[10] Abdul-Mageed, M., Elmadany, A., & Nagoudi, E. M. B. (2021).
*ARBERT & MARBERT: Deep Bidirectional Transformers for Arabic.* In
Proceedings of ACL-IJCNLP 2021, pp. 7088–7105.

[11] Conneau, A. et al. (2020). *Unsupervised Cross-lingual
Representation Learning at Scale.* In Proceedings of ACL 2020,
pp. 8440–8451.

---

*— End of Project Report —*
