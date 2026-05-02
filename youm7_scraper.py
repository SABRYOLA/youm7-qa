"""
youm7_scraper.py
================
Selenium-based scraper for اليوم السابع (Youm7) — Arabic news website.
Uses headless Chrome (auto-installed via webdriver-manager) so JavaScript-
rendered content is captured. All cleaning, metadata, and output logic
are preserved from the requests version.

Run with:
    python youm7_scraper.py
"""

import csv
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Make Arabic safe to print on Windows consoles (cp1252 default).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://www.youm7.com/"
ALLOWED_DOMAIN = "youm7.com"

SEED_SECTIONS = [
    ("https://www.youm7.com/Section/سياسة/319/1", "سياسة"),
    ("https://www.youm7.com/Section/اقتصاد-وبورصة/297/1", "اقتصاد"),
    ("https://www.youm7.com/Section/أخبار-الرياضة/298/1", "رياضة"),
    ("https://www.youm7.com/Section/علوم-و-تكنولوجيا/328/1", "تكنولوجيا"),
    ("https://www.youm7.com/Section/صحة-وطب/245/1", "صحة"),
    ("https://www.youm7.com/", "عام"),
]

LINK_SELECTORS = [
    "h3 a", "h2 a", ".story-title a", ".news-title a",
    "a.title", ".card-title a", "article a", ".item-title a",
]

# Selectors we wait for after navigation. We wait for actual content (a <p>
# inside a body container, or rendered link cards on listing pages) — not just
# the page shell, since the <article> tag often exists before its text loads.
WAIT_SELECTORS = [
    "h3 a", ".story-title", "article",
    "#articleBody p", ".news-content p", ".article-content p",
]
WAIT_TIMEOUT = 10  # seconds

USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) "
    "Gecko/20100101 Firefox/124.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    # Chrome on Android
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
]

BODY_CONTAINER_SELECTORS = [
    ".article-content",
    ".story-content",
    "#articleBody",
    ".news-content",
    ".content-body",
    "article",
    ".col-content",
    "main",
]

DECOMPOSE_TAGS = [
    "script", "style", "noscript", "iframe", "nav", "header",
    "footer", "aside", "form", "button", "svg", "canvas",
]

# Word-boundary anchored so tokens match whole class names like "social-share"
# but not substrings like "selectionShareable" (a JS-added feature on Youm7
# article paragraphs) or "header"/"loaded" (which contain "ad").
NOISE_PATTERN = re.compile(
    r"\b(?:ad|banner|social|share|sidebar|comment|cookie|popup|"
    r"newsletter|related|breadcrumb|pagination|menu|navbar|"
    r"toolbar|widget|tags|author-box|most-read)\b",
    re.I,
)

BLOCK_MARKERS = [
    "access denied", "forbidden", "just a moment",
    "verifying you are human", "captcha",
]

MAX_ARTICLES = 30
PER_SEED_LIMIT = 6  # 5 sections × 6 = 30, so every category gets coverage
MIN_FRAGMENT_LEN = 40
MIN_BODY_LEN = 150
DELAY_RANGE = (1.5, 3.0)
SCROLL_PAUSE = 1.0  # seconds after scroll, to let lazy content render

OUTPUT_DIR = "output"
JSON_PATH = os.path.join(OUTPUT_DIR, "youm7_corpus.json")
CSV_PATH = os.path.join(OUTPUT_DIR, "youm7_corpus.csv")
STATS_PATH = os.path.join(OUTPUT_DIR, "youm7_stats.txt")

CSV_COLUMNS = [
    "site", "source_name", "category", "language", "url", "title",
    "word_count", "char_count", "scraped_at", "body",
]


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("youm7_scraper")
# Quiet down webdriver-manager / selenium chatter.
logging.getLogger("WDM").setLevel(logging.WARNING)
logging.getLogger("selenium").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Driver setup & navigation
# ---------------------------------------------------------------------------

def build_driver() -> webdriver.Chrome:
    """Create a headless Chrome driver with Arabic locale and anti-detection flags."""
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationDetection")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--lang=ar-EG,ar")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--log-level=3")

    # Initial UA — rotated per-navigation via CDP below.
    opts.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")

    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_experimental_option(
        "prefs",
        {"intl.accept_languages": "ar-EG,ar,en-US;q=0.8,en;q=0.7"},
    )

    logger.info("Installing/locating ChromeDriver via webdriver-manager...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(40)

    # Hide the webdriver navigator flag.
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', "
                   "{get: () => undefined});"},
    )

    # Set the Arabic-browser header set globally.
    driver.execute_cdp_cmd(
        "Network.setExtraHTTPHeaders",
        {"headers": {
            "Accept-Language": "ar,ar-EG;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "Referer": BASE_URL,
        }},
    )

    return driver


def warmup(driver: webdriver.Chrome) -> None:
    """Load the homepage once so the site sees a normal browsing pattern."""
    logger.info("Warming up session on homepage: %s", BASE_URL)
    try:
        driver.get(BASE_URL)
        time.sleep(random.uniform(1.0, 2.0))
        logger.info("Warmup complete; title=%r", driver.title[:60])
    except WebDriverException as exc:
        logger.warning("Warmup failed: %s", exc)


def is_blocked_page(html: str, title: str) -> bool:
    """Return True if the response looks like a soft block / captcha page."""
    if not html or len(html) < 500:
        return True
    blob = (title + " " + html[:5000]).lower()
    return any(m in blob for m in BLOCK_MARKERS)


def fetch_page(driver: webdriver.Chrome, url: str, referer: str = BASE_URL):
    """Navigate to URL, wait for content, scroll once, return page source.

    Returns the rendered HTML on success, "BLOCKED" if the page looks like
    an access-denied / captcha interstitial, or None on any other failure.
    """
    time.sleep(random.uniform(*DELAY_RANGE))

    # Rotate UA + refresh Referer for this navigation.
    try:
        driver.execute_cdp_cmd(
            "Network.setUserAgentOverride",
            {"userAgent": random.choice(USER_AGENTS)},
        )
        driver.execute_cdp_cmd(
            "Network.setExtraHTTPHeaders",
            {"headers": {
                "Accept-Language": "ar,ar-EG;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
                "Referer": referer,
            }},
        )
    except WebDriverException as exc:
        logger.warning("CDP header override failed: %s", exc)

    try:
        driver.get(url)
    except TimeoutException:
        logger.warning("Page load timed out: %s", url)
        return None
    except WebDriverException as exc:
        logger.warning("Navigation error for %s: %s", url, exc)
        return None

    # Wait up to WAIT_TIMEOUT for any of the known content selectors.
    wait_css = ", ".join(WAIT_SELECTORS)
    try:
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, wait_css))
        )
    except TimeoutException:
        logger.info("No content selectors appeared within %ds on %s",
                    WAIT_TIMEOUT, url)

    # Trigger lazy-loaded content.
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(SCROLL_PAUSE)
    except WebDriverException:
        pass

    html = driver.page_source
    title = driver.title or ""

    if is_blocked_page(html, title):
        logger.warning("Page looks blocked (title=%r): %s", title[:80], url)
        return "BLOCKED"

    return html


# ---------------------------------------------------------------------------
# Link discovery
# ---------------------------------------------------------------------------

def is_valid_article_url(url: str) -> bool:
    """Return True if URL is on youm7.com and points to a story or section page."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if not parsed.netloc.endswith(ALLOWED_DOMAIN):
        return False
    if "/story/" not in url and "/Section/" not in url:
        return False
    return True


def discover_links(driver: webdriver.Chrome) -> list:
    """Visit every seed URL and collect (url, category) pairs.

    First tries the configured CSS selectors on each seed, then falls back
    to any anchor whose href contains "/story/". Each link is tagged with
    the category of the seed it was found on. A per-seed cap ensures every
    category is represented within the global cap.
    """
    results = []
    seen = set()

    def _add(href: str, base: str, category: str, seed_count: int) -> int:
        full = urljoin(base, href).split("#")[0]
        if not is_valid_article_url(full):
            return seed_count
        if "/story/" not in full:
            return seed_count
        if full in seen:
            return seed_count
        seen.add(full)
        results.append((full, category))
        return seed_count + 1

    for seed, category in SEED_SECTIONS:
        if len(results) >= MAX_ARTICLES:
            break
        logger.info("Discovering links from seed: %s (%s)", seed, category)
        html = fetch_page(driver, seed, referer=BASE_URL)
        if html is None or html == "BLOCKED":
            continue
        soup = BeautifulSoup(html, "lxml")

        all_anchors = soup.find_all("a", href=True)
        story_anchors = [a for a in all_anchors if "/story/" in a["href"]]
        logger.info("  page %d bytes, %d <a> tags, %d contain /story/",
                    len(html), len(all_anchors), len(story_anchors))

        if not story_anchors:
            logger.warning(
                "  seed returned no /story/ links — possible soft block or "
                "stripped response. <title>=%r",
                (soup.title.get_text(strip=True) if soup.title else ""),
            )

        seed_count = 0

        # Pass 1: configured selectors.
        for selector in LINK_SELECTORS:
            for a in soup.select(selector):
                href = a.get("href")
                if not href:
                    continue
                seed_count = _add(href, seed, category, seed_count)
                if seed_count >= PER_SEED_LIMIT or len(results) >= MAX_ARTICLES:
                    break
            if seed_count >= PER_SEED_LIMIT or len(results) >= MAX_ARTICLES:
                break

        # Pass 2: fallback — any anchor pointing at /story/.
        if seed_count < PER_SEED_LIMIT and len(results) < MAX_ARTICLES:
            for a in story_anchors:
                seed_count = _add(a["href"], seed, category, seed_count)
                if seed_count >= PER_SEED_LIMIT or len(results) >= MAX_ARTICLES:
                    break

        logger.info("  collected %d link(s) from this seed", seed_count)

    logger.info("Discovered %d unique article links across %d categories",
                len(results), len({c for _, c in results}))
    return results[:MAX_ARTICLES]


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def remove_noise(soup: BeautifulSoup) -> None:
    """Strip scripts, layout chrome, and elements matching the noise pattern."""
    for tag_name in DECOMPOSE_TAGS:
        for tag in list(soup.find_all(tag_name)):
            tag.decompose()

    for el in list(soup.find_all(True)):
        if el.attrs is None:
            continue
        attrs = []
        cls = el.attrs.get("class")
        if cls:
            attrs.append(" ".join(cls))
        eid = el.attrs.get("id")
        if eid:
            attrs.append(eid)
        if attrs and NOISE_PATTERN.search(" ".join(attrs)):
            el.decompose()


def normalize_whitespace(text: str) -> str:
    """Collapse runs of spaces/tabs into one space and 3+ newlines into two."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_body(soup: BeautifulSoup) -> str:
    """Find the main article container and return its cleaned, joined text."""
    container = None
    for sel in BODY_CONTAINER_SELECTORS:
        container = soup.select_one(sel)
        if container is not None:
            break
    if container is None:
        return ""

    fragments = []
    for el in container.find_all(["p", "h1", "h2", "h3", "h4", "li", "blockquote", "span"]):
        if el.name == "span":
            classes = el.get("class") or []
            if "article-p" not in classes:
                continue
        text = el.get_text(" ", strip=True)
        if len(text) < MIN_FRAGMENT_LEN:
            continue
        fragments.append(text)

    body = "\n\n".join(fragments)
    return normalize_whitespace(body)


def extract_title(soup: BeautifulSoup) -> str:
    """Return the article title from <h1>, falling back to <title>."""
    h1 = soup.find("h1")
    if h1:
        text = h1.get_text(" ", strip=True)
        if text:
            return text
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(" ", strip=True)
    return ""


# ---------------------------------------------------------------------------
# Article scraping
# ---------------------------------------------------------------------------

def scrape_article(driver: webdriver.Chrome, url: str, category: str):
    """Fetch one article URL and return a metadata dict, or None on failure.

    Returns the string "BLOCKED" if the page looks like a block page.
    """
    html = fetch_page(driver, url, referer=BASE_URL)
    if html == "BLOCKED":
        return "BLOCKED"
    if html is None:
        return None

    soup = BeautifulSoup(html, "lxml")
    title = extract_title(soup)
    remove_noise(soup)
    body = extract_body(soup)

    if len(body) < MIN_BODY_LEN:
        logger.info("Skipping (body too short, %d chars): %s", len(body), url)
        return None

    return {
        "site": "youm7",
        "source_name": "اليوم السابع",
        "category": category,
        "language": "ar",
        "url": url,
        "title": title,
        "body": body,
        "char_count": len(body),
        "word_count": len(body.split()),
        "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def ensure_output_dir() -> None:
    """Create the output/ folder if it does not already exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_json(documents: list) -> None:
    """Write all documents to youm7_corpus.json with real Arabic characters."""
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)
    logger.info("Wrote %s", JSON_PATH)


def save_csv(documents: list) -> None:
    """Write documents to youm7_corpus.csv using utf-8-sig for Excel."""
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for doc in documents:
            writer.writerow({col: doc.get(col, "") for col in CSV_COLUMNS})
    logger.info("Wrote %s", CSV_PATH)


def build_stats(documents: list) -> str:
    """Return a human-readable plain-text statistics report for the run."""
    total = len(documents)
    total_words = sum(d["word_count"] for d in documents)
    total_chars = sum(d["char_count"] for d in documents)
    avg_words = (total_words / total) if total else 0

    by_cat = {}
    for d in documents:
        by_cat[d["category"]] = by_cat.get(d["category"], 0) + 1

    lines = []
    lines.append("=" * 60)
    lines.append("Youm7 Scraper — Run Summary")
    lines.append("=" * 60)
    lines.append(f"Run timestamp     : {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    lines.append(f"Total articles    : {total}")
    lines.append(f"Total words       : {total_words}")
    lines.append(f"Total characters  : {total_chars}")
    lines.append(f"Avg words/article : {avg_words:.1f}")
    lines.append("")
    lines.append("Articles by category:")
    for cat, count in sorted(by_cat.items(), key=lambda kv: -kv[1]):
        lines.append(f"  - {cat}: {count}")
    lines.append("")
    lines.append("Scraped URLs:")
    for d in documents:
        lines.append(f"  - {d['url']}")
    lines.append("=" * 60)
    return "\n".join(lines)


def save_stats(report: str) -> None:
    """Persist the stats report to youm7_stats.txt."""
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info("Wrote %s", STATS_PATH)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run end-to-end: launch Chrome, discover, scrape, clean, and write output."""
    ensure_output_dir()

    driver = None
    try:
        driver = build_driver()
        warmup(driver)

        links = discover_links(driver)
        if not links:
            logger.error("No article links discovered — aborting.")
            return

        documents = []
        blocked_count = 0
        attempted = 0

        for i, (url, category) in enumerate(links, start=1):
            logger.info("[%d/%d] (%s) Scraping %s", i, len(links), category, url)
            attempted += 1
            result = scrape_article(driver, url, category)
            if result == "BLOCKED":
                blocked_count += 1
                continue
            if result is None:
                continue
            documents.append(result)

        if attempted > 0 and blocked_count == attempted:
            print("⚠️  يبدو أن الموقع يحجب طلبات السيرفر. شغّل السكريبت من جهازك الشخصي.")
            return

        if not documents:
            logger.error("No articles successfully scraped.")
            return

        save_json(documents)
        save_csv(documents)
        report = build_stats(documents)
        save_stats(report)
        print(report)
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()
