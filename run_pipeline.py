"""
run_pipeline.py
===============
Runs all five Youm7 QA stages end-to-end with progress and timing.

Stages:
  1. youm7_scraper.py   — Selenium scrape (~3–5 minutes)
  2. preprocess.py      — Arabic cleaning + chunking (~10 seconds)
  3. embed.py           — embeddings + FAISS index (~1–2 minutes first run)
  4. answer.py          — extractive QA on test questions (~10 seconds)
  5. api.py             — FastAPI server (runs in foreground, Ctrl+C to stop)

If any stage fails the pipeline halts immediately with an actionable
error message. Stage 5 (the API server) is started last and stays in
the foreground.

Run with:
    python run_pipeline.py
"""

import subprocess
import sys
import time
from pathlib import Path

# UTF-8 console for Arabic on Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent

STAGES = [
    {"num": 1, "name": "Data Collection",       "script": "youm7_scraper.py"},
    {"num": 2, "name": "Preprocessing",         "script": "preprocess.py"},
    {"num": 3, "name": "Embedding",             "script": "embed.py"},
    {"num": 4, "name": "Answer Generation",     "script": "answer.py"},
    {"num": 5, "name": "API Server",            "script": "api.py"},
]


def fmt_duration(seconds: float) -> str:
    """Render a duration as `Xm Ys` (e.g. `4m 32s`)."""
    seconds = int(seconds)
    return f"{seconds // 60}m {seconds % 60}s"


def print_header() -> None:
    """Print the pipeline-runner banner."""
    print("╔══════════════════════════════════════════════════╗")
    print("║   Youm7 QA — Full Pipeline Runner                ║")
    print("║   Running all 5 stages automatically             ║")
    print("╚══════════════════════════════════════════════════╝")
    print()


def run_stage(stage: dict, total: int) -> float:
    """Run one stage as a subprocess; return its elapsed time on success.

    Exits the whole process with code 1 on failure, after printing the
    failed stage's number and remediation instructions.
    """
    num, name, script = stage["num"], stage["name"], stage["script"]
    print(f"[{num}/{total}] Running Stage {num} — {name}...")
    print("─" * 52)

    if not (PROJECT_ROOT / script).exists():
        print(f"❌ Pipeline stopped at Stage {num}")
        print(f"   Missing file: {script}")
        print(f"   Make sure you cloned the full repo and run from its root.")
        sys.exit(1)

    start = time.time()
    try:
        subprocess.check_call([sys.executable, script], cwd=str(PROJECT_ROOT))
    except subprocess.CalledProcessError as exc:
        elapsed = time.time() - start
        print()
        print(f"❌ Pipeline stopped at Stage {num} ({name}) after {fmt_duration(elapsed)}")
        print(f"   {script} exited with code {exc.returncode}")
        print(f"   Fix the error above and re-run:")
        print(f"      python {script}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n⚠️  Stage {num} interrupted by user (Ctrl+C). Exiting.")
        sys.exit(130)

    elapsed = time.time() - start
    print(f"✅ Stage {num} complete (took {fmt_duration(elapsed)})\n")
    return elapsed


def print_final_banner(total_elapsed: float) -> None:
    """Print the success banner shown right before the API takes over the terminal."""
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║   Pipeline Complete! ✅                          ║")
    print(f"║   Total time: {fmt_duration(total_elapsed):<35}║")
    print("║                                                  ║")
    print("║   Your API is running at:                        ║")
    print("║   http://localhost:8000                          ║")
    print("║   http://localhost:8000/docs  (Swagger UI)       ║")
    print("║   http://localhost:8000/health                   ║")
    print("║                                                  ║")
    print("║   Open index.html to use the Arabic UI           ║")
    print("║   Press Ctrl+C in this terminal to stop the API  ║")
    print("╚══════════════════════════════════════════════════╝")
    print()


def main() -> None:
    """Run stages 1–4 in sequence, then start stage 5 in foreground."""
    print_header()

    pipeline_start = time.time()
    total = len(STAGES)

    # Stages 1–4 run as plain subprocesses.
    for stage in STAGES[:-1]:
        run_stage(stage, total)

    # Stage 5 (API) is interactive — print the banner first, then exec.
    last = STAGES[-1]
    print(f"[{last['num']}/{total}] Starting Stage {last['num']} — {last['name']}...")
    print_final_banner(time.time() - pipeline_start)

    try:
        subprocess.check_call([sys.executable, last["script"]], cwd=str(PROJECT_ROOT))
    except KeyboardInterrupt:
        print("\nAPI server stopped (Ctrl+C). Goodbye! 👋")
    except subprocess.CalledProcessError as exc:
        print(f"\n❌ API server exited with code {exc.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
