"""Live probe: ph.indeed.com + www.glassdoor.com review pages in real Chrome.

Verdict per site: reviews present? captcha/block? embedded JSON payload?
Saves HTML snapshots to .storage/ for extractor development.
"""
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

STORAGE = Path(__file__).resolve().parent / ".storage"

TARGETS = [
    ("indeed", "https://ph.indeed.com/cmp/Accenture/reviews",
     ["comp-initialData", "pros", "cons"]),
    ("glassdoor", "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138.htm",
     ["reviewText", "pros", "cons", "ReviewContext"]),
]

BLOCK_RE = re.compile(r"unusual traffic|verify you are human|captcha|"
                      r"are you a robot|automated access|access denied|"
                      r"too many requests|blocked", re.I)


def probe(page, name, url, markers):
    print(f"\n=== {name}: {url}")
    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(6000)
        title = page.title()
        html = page.content()
        (STORAGE / f"live_{name}.html").write_text(html, encoding="utf-8")
        block = BLOCK_RE.findall(html[:200000])
        found = {m: len(re.findall(re.escape(m), html, re.I)) for m in markers}
        print(f"  title: {title!r}")
        print(f"  html bytes: {len(html)}")
        print(f"  block markers: {block[:5] if block else 'NONE'}")
        print(f"  payload markers: {found}")
        # count visibly rendered review cards
        for sel in ["div[data-testid='RallyReviewCard']",
                    "div.ReviewCard", "div[data-test='ReviewCard']",
                    "li.hero-review", "div.hero-review"]:
            n = page.locator(sel).count()
            if n:
                print(f"  cards via {sel}: {n}")
        return html
    except Exception as e:  # noqa: BLE001
        print(f"  ERROR: {e}")
        return ""


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=False)
    ctx = browser.new_context(locale="en-US")
    page = ctx.new_page()
    for name, url, markers in TARGETS:
        probe(page, name, url, markers)
        time.sleep(3)
    browser.close()
print("\nDONE")
