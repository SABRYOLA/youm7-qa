# Contributing to Youm7 QA
## دليل المساهمة

Thank you for considering a contribution to this project! All contributions
are welcome — bug reports, feature suggestions, new website scrapers,
documentation fixes, and translation improvements.

شكراً لاهتمامك بالمساهمة في هذا المشروع. كل المساهمات مرحَّب بها — تقارير
الأخطاء، اقتراحات الميزات، إضافة مواقع جديدة، تحسينات التوثيق، والترجمة.

---

## How to Contribute — كيف تساهم؟

1. **Fork** this repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/youm7-qa.git
   cd youm7-qa
   ```
3. **Create a branch** for your change:
   ```bash
   git checkout -b feature/short-description
   # or: git checkout -b fix/short-description
   ```
4. **Set up the environment**:
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   python setup.py
   ```
5. **Make your change**, run the relevant scripts to verify it works.
6. **Commit** with a clear message in English or Arabic:
   ```bash
   git commit -m "Add: support for المصري اليوم"
   git commit -m "Fix: chunk overlap off-by-one"
   ```
7. **Push** your branch and open a **Pull Request** against `main` on the
   upstream repo.

---

## Adding a New Website — إضافة موقع جديد

The scraper is currently hard-coded to *اليوم السابع*. Adding a new site
involves five steps. Use Youm7 as the reference implementation.

### Step 1 — Add a new entry to `SEED_SECTIONS` in `youm7_scraper.py`

If you only want to add one site, edit `youm7_scraper.py`. If you want
multiple sites, factor it into a `SITES` dict like this:

```python
SITES = {
    "youm7": {
        "name": "اليوم السابع",
        "base_url": "https://www.youm7.com/",
        "domain": "youm7.com",
        "seed_sections": [
            ("https://www.youm7.com/Section/سياسة/319/1", "سياسة"),
            ("https://www.youm7.com/Section/اقتصاد-وبورصة/297/1", "اقتصاد"),
            # ...
        ],
        "body_selectors": [".article-content", "#articleBody", ...],
        "title_selectors": ["h1"],
    },
    "your_site": {
        "name": "اسم الموقع",
        "base_url": "https://www.example.com/",
        "domain": "example.com",
        "seed_sections": [
            ("https://www.example.com/section/politics", "سياسة"),
            # ...
        ],
        "body_selectors": [".article-body", "main article"],
        "title_selectors": ["h1.headline"],
    },
}
```

### Step 2 — Identify the right CSS selectors

Open the target site in your browser, right-click an article body, and
inspect. Find a stable selector that wraps the article text. Common
candidates: `.article-content`, `#articleBody`, `[itemprop="articleBody"]`,
`main article`, `.post-content`. Test multiple article URLs — selectors
must be consistent across articles.

### Step 3 — Test the link discovery

Run the scraper and check the log. You should see lines like:

```
[INFO]   page 149904 bytes, 198 <a> tags, 127 contain /story/
[INFO]   collected 6 link(s) from this seed
```

If "0 contain /story/", the URL pattern is different — adjust the
`is_valid_article_url` function.

### Step 4 — Verify the extracted body

Look at `output/youm7_corpus.json` (or your equivalent). Each article's
`body` field should contain real prose. If it's empty or contains
navigation/sidebar text, your body selectors are wrong.

### Step 5 — Update `verify_preprocess.py` if needed

If you change the chunk schema or add new categories, update the
verification script's category list.

---

## Improving the Model — تحسين النموذج

The default embedder is `paraphrase-multilingual-MiniLM-L12-v2` (384-dim,
~120 MB). To swap it:

1. **Edit `embed.py` and `answer.py`** — change the `MODEL_NAME` constant.
   Both files must use the **same** model.
2. **Pick a compatible model** — any sentence-transformer that supports
   Arabic. Tested options:
   - `paraphrase-multilingual-mpnet-base-v2` — 768-dim, ~470 MB, slower
     but slightly higher recall.
   - `intfloat/multilingual-e5-small` — 384-dim, ~120 MB, comparable.
   - `sentence-transformers/distiluse-base-multilingual-cased-v2` —
     512-dim, ~480 MB.
3. **Re-run the pipeline** so the FAISS index uses the new dimensions:
   ```bash
   python embed.py
   ```
   The index is rebuilt from scratch — no migration needed.
4. **Sanity-check** the test questions in `answer.py` — confidence scores
   will change but the relative ranking should stay sensible.

---

## Reporting Bugs — الإبلاغ عن الأخطاء

Open a [bug report issue](.github/ISSUE_TEMPLATE/bug_report.md). Include:

- Which stage failed (`1`–`5`)
- Operating system and version (e.g. `Windows 11 Pro 26200`)
- Python version (`python --version`)
- The full error message — copy-paste, do not paraphrase
- The exact command you ran
- Steps to reproduce (minimal example)
- What you expected vs what actually happened

Bugs without a copy-pasted error message are very hard to debug — please
include it.

---

## Pull Request Guidelines — قواعد طلبات الدمج

- **One PR = one logical change.** Don't bundle a bug fix and a new
  feature in the same PR.
- **Title convention**: prefix with `Add:`, `Fix:`, `Refactor:`, `Docs:`,
  or `Test:`.
- **Description** must explain *what* and *why*. The diff already shows
  *how*.
- **Test it** locally — at minimum run the affected stages and confirm
  the output files still parse.
- **No bundled large files**: do not commit `.faiss`, `.bin`, scraped
  HTML, or your `.venv/`. The `.gitignore` covers all of these but
  double-check `git status` before pushing.
- **Update docs** if you change a public interface (an API endpoint,
  a CLI flag, a function signature).

---

## Code Style — أسلوب الكتابة

- **Python 3.10+** — use modern syntax (`match` statements, `|` unions,
  walrus operator if it helps).
- **Use `logging`, not `print`** for diagnostic output. `print` is fine
  for the final user-facing summary banners.
- **Docstrings on every function** — one short line is enough, but every
  function must have one.
- **Type hints** are encouraged but not required — the project uses them
  inconsistently and that's OK.
- **Arabic comments are welcome** — write them right-to-left in your
  editor and they will render correctly. Mixed Arabic/English in the
  same comment is also fine.
- **Format with `black`** if you have it installed (line length 88).
- **Never silently swallow exceptions.** Log them and re-raise, or
  return a clearly-marked error sentinel.

---

## Code of Conduct

Be respectful. Disagree with ideas, not people. Arabic NLP is a small
community — let's keep it welcoming.

كن محترماً. اختلف مع الأفكار لا مع الأشخاص.

---

## Questions?

Open a [feature request issue](.github/ISSUE_TEMPLATE/feature_request.md)
or start a discussion on the repo. There are no stupid questions.
