"""Probe C-1/C-2/C-3/C-4/C-6: browser pass (own profile browser_profile_c).

Sites: kalibrr company page, glints company page (real pattern from search:
glints.com/companies/<slug>/<uuid>), bossjob, careerbliss.
Headless chromium with dedicated persistent profile. Save HTML to .storage.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
STORAGE = HERE / ".storage"
PROFILE = STORAGE / "browser_profile_c"
PROFILE.mkdir(parents=True, exist_ok=True)

TASKS = [
    # (tag, url, wait_ms)
    ("kalibrr_home", "https://www.kalibrr.com/", 4000),
    ("kalibrr_co", "https://www.kalibrr.com/home/company/globant", 6000),
    ("glints_glints_co", "https://glints.com/companies/glints/db947fbf-44c6-4656-8729-2bdfc45cd6b1", 6000),
    ("glints_sitemap", "https://www.glints.com/sitemap.xml", 3000),
    ("bossjob", "https://www.bossjob.ph/", 5000),
    ("careerbliss", "https://www.careerbliss.com/", 5000),
]

KW = ["review", "Review", "reviews", "Pros", "Cons", "pros", "cons",
      "rating", "Rating", "Job Title", "job title", "Current employee",
      "Former employee", "employee review", "Write a review", "Philippines"]


def P(*a):
    print(" ".join(str(y) if isinstance(y, (int, float)) else ascii(str(y))
                   for y in a))


def summarize(tag: str, page) -> None:
    try:
        html = page.content()
    except Exception as e:
        P(tag, "content ERR", type(e).__name__)
        return
    body = ""
    try:
        body = page.inner_text("body")
    except Exception:
        pass
    P("\n===", tag, page.url)
    P("  html_len=", len(html), " body_len=", len(body),
      " title=", page.title()[:100])
    for kw in KW:
        n = html.count(kw)
        if n:
            P("   kw", kw, n)
    # review-ish links
    try:
        hrefs = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => e.getAttribute('href'))")
    except Exception:
        hrefs = []
    hrefs = [h for h in hrefs if h]
    intr = sorted({h for h in hrefs if re.search(
        r"review|rating|companies|company|employer|profil", h, re.I)})
    P("   links total=", len(hrefs), " interesting=", len(intr))
    for h in intr[:20]:
        P("     ", h[:150])
    # date-ish lines in visible text (proof of dated content)
    dates = sorted(set(re.findall(
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+20\d{2}\b"
        r"|\b20\d{2}-\d{2}-\d{2}\b", body)))
    P("   dates in body:", len(dates), "sample:", dates[:8])
    out = STORAGE / f"c_{tag}.html"
    try:
        out.write_text(html, encoding="utf-8")
        P("   saved", out.name)
    except Exception as e:
        P("   save ERR", e)


def main() -> None:
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE),
            headless=True,
            channel="chrome",
            locale="en-US",
            viewport={"width": 1366, "height": 900},
        )
        page = ctx.new_page()
        for tag, url, wait in TASKS:
            try:
                resp = page.goto(url, timeout=45000, wait_until="domcontentloaded")
                page.wait_for_timeout(wait)
                P("\n>>>", tag, url, "status=", resp.status if resp else "?")
                summarize(tag, page)
            except Exception as e:
                P("\n>>>", tag, url, "ERR", type(e).__name__, str(e)[:200])
            time.sleep(2.5)
        ctx.close()
    P("\nDONE")


if __name__ == "__main__":
    main()
