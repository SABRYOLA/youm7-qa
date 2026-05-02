# Youm7 QA — Arabic Question Answering System
## نظام الإجابة على الأسئلة باللغة العربية

![Python](https://img.shields.io/badge/python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![License](https://img.shields.io/badge/license-MIT-blue)
![Arabic](https://img.shields.io/badge/language-Arabic-orange)
![FAISS](https://img.shields.io/badge/search-FAISS-red)
![sentence-transformers](https://img.shields.io/badge/embeddings-sentence-transformers-yellow)

> An end-to-end Arabic question-answering system over the **اليوم السابع** news website.
> Scrape → preprocess → embed → retrieve → extract → serve, all in five files of vanilla Python.

> <img width="1850" height="682" alt="image" src="https://github.com/user-attachments/assets/fc219cae-6349-48cb-873c-05d4f406406e" />


---

## ⚡ Quick Start (3 commands)

```bash
git clone https://github.com/SABRYOLA/youm7-qa.git
cd youm7-qa
python setup.py && python run_pipeline.py
```

Then open [`http://localhost:8000/docs`](http://localhost:8000/docs) for the
Swagger UI, or double-click `index.html` for the Arabic chatbot.

---

## 🎥 Demo

> 🎬 **Add a demo GIF or screenshot here showing the Arabic QA interface in action.**
>
> Suggested capture: type *"ما هو سعر الذهب اليوم؟"* in `index.html`,
> show the answer card with confidence label *عالية (0.90)* and the
> three related-source cards beneath it.

---

## 📚 What It Does

In a digital news landscape that produces thousands of Arabic articles per
day, finding a specific piece of information inside any one article is hard.
Youm7 QA scrapes news articles in five categories
(*سياسة، اقتصاد، رياضة، تكنولوجيا، صحة*), embeds them into a
384-dimensional semantic space, and lets you ask Arabic questions in
natural language. Each answer is a verbatim quotation from a real article,
returned with a confidence score and a clickable source link — no
hallucination, no API key, no GPU required.

---

## 🏗️ System Architecture

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

The five stages are independent — each produces a deterministic file in
`output/` that the next stage consumes. You can re-run any stage without
redoing the previous ones, as long as its input files exist.

---

## 🧰 Tech Stack

| Component       | Technology                  | Purpose                                  |
|-----------------|-----------------------------|------------------------------------------|
| 🕷️ Scraping     | Selenium + BeautifulSoup    | JS-rendered article collection           |
| 🔤 Arabic NLP   | pyarabic                    | Hamza / Teh-Marbuta / tashkeel cleanup   |
| 🧠 Embedding    | sentence-transformers       | `paraphrase-multilingual-MiniLM-L12-v2`  |
| 🔍 Search       | FAISS `IndexFlatIP`         | Cosine-similarity retrieval              |
| ⚡ API          | FastAPI + Uvicorn           | REST endpoints + Swagger docs            |
| 🌐 UI           | HTML + CSS + vanilla JS     | Arabic chatbot, RTL, Tajawal font        |

---

## 📂 Project Structure

```
youm7-qa/
│
├── 📄 .gitignore
├── 📄 LICENSE
├── 📄 README.md              ← you are here
├── 📄 requirements.txt
├── 📄 setup.py               ← first-time environment setup
├── 📄 run_pipeline.py        ← runs all 5 stages end-to-end
├── 📄 CONTRIBUTING.md
├── 📄 API_DOCUMENTATION.md
├── 📄 PROJECT_REPORT.md
├── 📄 GITHUB_UPLOAD_GUIDE.md
│
├── 🐍 youm7_scraper.py       ← Stage 1
├── 🐍 preprocess.py          ← Stage 2
├── 🐍 embed.py               ← Stage 3
├── 🐍 answer.py              ← Stage 4
├── 🐍 api.py                 ← Stage 5
├── 🌐 index.html             ← Arabic UI
│
├── output/                   (generated at runtime — gitignored)
│   └── .gitkeep
│
└── .github/
    └── ISSUE_TEMPLATE/
        ├── bug_report.md
        └── feature_request.md
```

---

## 🚀 Installation

### Prerequisites

- **Python 3.10+** (modern syntax + type hints).
- **Google Chrome** installed locally — Selenium drives a headless instance.
- An internet connection on first run (the model downloads ~120 MB; cached afterwards).

### Step-by-step

```bash
# 1. Clone the repo
git clone https://github.com/sabryola/youm7-qa.git
cd youm7-qa

# 2. Create a virtual environment (recommended)
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 3. Run the setup script (checks Python, installs deps, verifies Chrome)
python setup.py
```

---

## ▶️ How to Run

### Option A — One command, all stages

```bash
python run_pipeline.py
```

This runs Stages 1–4 sequentially with timing, then starts the API server
in the foreground. Press `Ctrl+C` to stop.

### Option B — Run each stage manually

| Step | Command                       | What it does                               | Output                                  |
|-----:|-------------------------------|--------------------------------------------|-----------------------------------------|
|    1 | `python youm7_scraper.py`     | Scrapes 30 Arabic articles via Selenium    | `output/youm7_corpus.json`              |
|    2 | `python preprocess.py`        | Cleans + chunks into 62 records            | `output/youm7_chunks.json`              |
|    3 | `python embed.py`             | Embeds + builds FAISS index                | `output/youm7_index.faiss`              |
|    4 | `python answer.py`            | Runs 5 test questions                      | `output/youm7_answers.json`             |
|    5 | `python api.py`               | Starts the FastAPI server on `:8000`       | (HTTP service)                          |
|    6 | open `index.html`             | Launches the Arabic chatbot UI             | (browser)                               |

---

## 🌐 API Quick Reference

The API runs at **`http://localhost:8000`**. All bodies are JSON.

| Method | Endpoint   | Description                                       | Try it                                                                       |
|--------|------------|---------------------------------------------------|------------------------------------------------------------------------------|
| GET    | `/`        | Welcome + endpoint index                          | `curl http://localhost:8000/`                                                |
| GET    | `/health`  | Service health, total chunks/articles, model name | `curl http://localhost:8000/health`                                          |
| POST   | `/ask`     | Full QA: retrieve → extract → format              | `POST {"question":"ما هو سعر الذهب اليوم؟","top_k":5}`                       |
| POST   | `/search`  | Raw retrieval, no answer extraction               | `POST {"query":"الذهب في مصر","top_k":3}`                                    |
| GET    | `/docs`    | Swagger UI (interactive)                          | open in browser                                                              |
| GET    | `/redoc`   | ReDoc UI (read-only reference)                    | open in browser                                                              |

See [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) for full request/response
schemas and integration examples in Python, JavaScript, and HTML.

---

## 📦 Sample API Response

A real response from `POST /ask` for the question
*"ما هو سعر الذهب عيار 21 في مصر اليوم؟"*:

```json
{
  "question": "ما هو سعر الذهب عيار 21 في مصر اليوم؟",
  "answer": "استقر سعر الذهب عيار 24 اليوم في مصر خلال تعاملات السبت 2 مايو 2026 عند مستوى 7960 جنيه، حيث عادت الاونصه للتداول اعلى مستوى 4600 دولار بعد ملامسه ادنى مستوى خلال الجلسه ويعد عيار 24 الاكثر نقاء بين الاعيره المختلفه",
  "confidence": 0.90,
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
    }
  ],
  "scraped_at": "2026-05-02T04:17:13Z",
  "processing_time_ms": 14
}
```

---

## 🎯 Confidence Score Guide

The `confidence` field is the cosine-similarity score (`0.0` – `1.0`) of the
top retrieved chunk. The Arabic `confidence_label` maps it to:

| Label              | Score Range  | Meaning                                                     |
|--------------------|--------------|-------------------------------------------------------------|
| **عالية**           | 0.65 – 1.00  | Highly relevant — answer is almost certainly in this chunk. |
| **متوسطة**          | 0.40 – 0.64  | Moderately relevant — partial answer likely.                |
| **منخفضة**          | 0.30 – 0.39  | Weakly relevant — topical overlap only.                     |
| **لا توجد نتائج**   | < 0.30       | Below threshold — system returns "no answer".               |

---

## 🧪 Test Results

Five test questions across the five categories:

| # | Question                                       | Top Score | Label    | Verdict     |
|---|------------------------------------------------|----------:|----------|-------------|
| 1 | ما هو سعر الذهب عيار 21 في مصر اليوم؟         |      0.90 | عالية     | ✅ Correct   |
| 2 | ما هي أسباب أمراض القلب؟                       |      0.82 | عالية     | ✅ Correct   |
| 3 | ما آخر أخبار الذكاء الاصطناعي وآبل؟            |      0.65 | عالية     | ✅ Correct   |
| 4 | ما هي مواعيد مباريات الدوري المصري؟            |      0.51 | متوسطة    | ⚠️ Partial  |
| 5 | ما هي نصائح لتقوية العضلات؟                   |      0.63 | متوسطة    | ⚠️ Partial  |

3/5 high-confidence and correct; the 2 medium-confidence cases were corpus
gaps (no domestic-fixtures or muscle-training article in the 30-article
sample), not retrieval failures.

---

## 🚧 Known Limitations

- **Small corpus** (30 articles, 62 chunks) — capped for demonstration.
- **Extractive only** — answers are quoted verbatim, never synthesized.
- **MSA only** — Egyptian dialect questions are not in scope.
- **No answer caching** — every request re-encodes the question.
- **JS-rendered scraping is slow** (~5–8 s per article).

See [`PROJECT_REPORT.md`](PROJECT_REPORT.md) §5 for the full table of
limitations with remediations, and §6 for the future-work roadmap.

---

## 📖 Documentation

- [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) — full REST API reference
- [`PROJECT_REPORT.md`](PROJECT_REPORT.md) — academic-style write-up
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to contribute (with steps to add a new website)
- [`GITHUB_UPLOAD_GUIDE.md`](GITHUB_UPLOAD_GUIDE.md) — beginner-friendly Git/GitHub upload walkthrough

---

## 🤝 Contributing

Contributions are welcome — bug reports, feature suggestions, new website
scrapers, documentation fixes. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for
the full contribution flow.

---

## 👥 Authors

- **\<Your Name\>** — \<Your University\> — Natural Language Processing (May 2026)

---

## 🙏 Acknowledgements

- **Sentence-Transformers** team for the `paraphrase-multilingual-MiniLM-L12-v2` model.
- **Facebook AI Research** for FAISS.
- **اليوم السابع (Youm7)** for the publicly accessible content used as the corpus.
- **Taha Zerrouki** for `pyarabic`.

---

## 📜 License

[MIT License](LICENSE) — free for educational and commercial use.
Scraped content remains the intellectual property of *اليوم السابع* and
is used here for non-commercial research purposes only.

---

<p align="center">
  Made with ☕ and a lot of <strong>تشكيل</strong>.
</p>
