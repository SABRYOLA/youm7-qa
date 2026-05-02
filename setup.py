"""
setup.py
========
First-time environment setup for the Youm7 QA project.

Performs five checks and one install step:
  1. Python version >= 3.10
  2. Creates the output/ directory if missing
  3. Installs all dependencies from requirements.txt
  4. Verifies Google Chrome is installed (needed by Selenium)
  5. Verifies every required project file is present

Run with:
    python setup.py
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# UTF-8 console for Arabic on Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = [
    "youm7_scraper.py",
    "preprocess.py",
    "embed.py",
    "answer.py",
    "api.py",
    "index.html",
    "requirements.txt",
]
MIN_PYTHON = (3, 10)


def step(label: str) -> None:
    """Print a step header."""
    print(f"\n[•] {label}")


def ok(msg: str) -> None:
    print(f"    ✅ {msg}")


def warn(msg: str) -> None:
    print(f"    ⚠️  {msg}")


def fail(msg: str) -> None:
    print(f"    ❌ {msg}")


def check_python() -> bool:
    """Verify the running Python interpreter is >= 3.10."""
    step("Checking Python version")
    cur = sys.version_info[:3]
    if cur >= MIN_PYTHON:
        ok(f"Python {cur[0]}.{cur[1]}.{cur[2]} (>= {MIN_PYTHON[0]}.{MIN_PYTHON[1]} required)")
        return True
    fail(f"Python {cur[0]}.{cur[1]}.{cur[2]} is too old. "
         f"Need Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ — install from https://python.org")
    return False


def ensure_output_dir() -> bool:
    """Create the output/ directory if it doesn't already exist."""
    step("Ensuring output/ directory exists")
    out = PROJECT_ROOT / "output"
    out.mkdir(exist_ok=True)
    ok(f"{out} ready")
    return True


def install_requirements() -> bool:
    """Install everything in requirements.txt via pip."""
    step("Installing dependencies from requirements.txt")
    req = PROJECT_ROOT / "requirements.txt"
    if not req.exists():
        fail(f"{req} not found")
        return False
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(req)]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as exc:
        fail(f"pip install failed (exit {exc.returncode})")
        return False
    ok("All dependencies installed")
    return True


def check_chrome() -> bool:
    """Best-effort check that Google Chrome is installed somewhere."""
    step("Checking for Google Chrome (needed by Selenium)")
    candidates = [
        "google-chrome",
        "google-chrome-stable",
        "chrome",
        "chromium",
        "chromium-browser",
    ]
    if sys.platform == "win32":
        candidates += [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
    elif sys.platform == "darwin":
        candidates += [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]

    for c in candidates:
        if shutil.which(c) or os.path.isfile(c):
            ok(f"Found: {c}")
            return True

    warn("Google Chrome was not found on this machine.")
    warn("Install it from https://www.google.com/chrome before running youm7_scraper.py.")
    warn("(Stages 2–5 do not require Chrome — only Stage 1 does.)")
    return True  # non-fatal


def check_required_files() -> bool:
    """Verify every required project file is present."""
    step("Verifying required project files")
    missing = [f for f in REQUIRED_FILES if not (PROJECT_ROOT / f).exists()]
    if missing:
        for m in missing:
            fail(f"Missing: {m}")
        return False
    ok(f"All {len(REQUIRED_FILES)} required files present")
    return True


def print_success() -> None:
    """Print the final next-steps banner."""
    banner = [
        "",
        "╔══════════════════════════════════════════════════╗",
        "║   Setup Complete! ✅                             ║",
        "║                                                  ║",
        "║   Run the pipeline in this order:                ║",
        "║   1. python youm7_scraper.py                     ║",
        "║   2. python preprocess.py                        ║",
        "║   3. python embed.py                             ║",
        "║   4. python answer.py                            ║",
        "║   5. python api.py                               ║",
        "║   6. Open index.html in your browser             ║",
        "║                                                  ║",
        "║   Or run everything at once:                     ║",
        "║      python run_pipeline.py                      ║",
        "╚══════════════════════════════════════════════════╝",
    ]
    print("\n".join(banner))


def main() -> int:
    """Run all setup steps in order; return process exit code."""
    print("Youm7 QA — Project Setup")
    print("=" * 56)

    steps = [
        check_python,
        check_required_files,
        ensure_output_dir,
        install_requirements,
        check_chrome,
    ]
    for fn in steps:
        if not fn():
            print("\n❌ Setup aborted. Fix the error above and re-run: python setup.py")
            return 1

    print_success()
    return 0


if __name__ == "__main__":
    sys.exit(main())
