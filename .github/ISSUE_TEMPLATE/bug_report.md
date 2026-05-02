---
name: 🐛 Bug Report
about: Report a problem with one of the pipeline stages or the API
title: "[BUG] <one-line summary>"
labels: bug
assignees: ''
---

## 🐛 Bug Description

<!-- Briefly describe what went wrong, in one or two sentences. -->

## 📌 Which Stage Failed?

<!-- Tick the one that broke. -->

- [ ] Stage 1 — `youm7_scraper.py` (Selenium scraper)
- [ ] Stage 2 — `preprocess.py` (Arabic preprocessing)
- [ ] Stage 3 — `embed.py` (embeddings + FAISS)
- [ ] Stage 4 — `answer.py` (answer generation)
- [ ] Stage 5 — `api.py` (FastAPI server)
- [ ] Frontend — `index.html`
- [ ] Setup — `setup.py` / `run_pipeline.py`
- [ ] Other / not sure

## 💻 Environment

| Item | Value |
|------|-------|
| Operating system   | <!-- e.g. Windows 11 Pro 26200, macOS 14.4, Ubuntu 22.04 --> |
| Python version     | <!-- run: python --version --> |
| Chrome version     | <!-- if Stage 1: chrome://settings/help --> |
| Project version    | <!-- git rev-parse --short HEAD, or release tag --> |
| Browser (frontend) | <!-- if frontend bug: Chrome/Edge/Firefox + version --> |

## 🧾 Error Message

<!-- Paste the FULL error / traceback verbatim. Do not paraphrase.
     Wrap it in a code fence so the formatting is preserved. -->

```
<paste here>
```

## 🔁 Steps to Reproduce

<!-- The minimal sequence of commands or actions to reproduce the bug. -->

1. ...
2. ...
3. ...

## ✅ Expected Behavior

<!-- What you thought would happen. -->

## ❌ Actual Behavior

<!-- What actually happened. -->

## 📷 Screenshots / Logs (optional)

<!-- Drag and drop images, paste log excerpts, or attach files. -->

## 💡 Additional Context (optional)

<!-- Anything else that might help — proxy/firewall? Custom config?
     Did this used to work and now doesn't? -->
