"""Round 2: Kalibrr /c/<slug> company pages + Glints /browse/company.

Answers: (a) does a reviews section exist with job title/date/location/text?
(b) any 2026 PH CS/IT examples? Own headless profile, no login.
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from playwright.sync_api import sync_playwright  # noqa: E402

STORAGE = Path(__file__).parent / ".storage"


def goto(page, url, wait=6000):
    print(f"\n=== {url}")
    try:
        page.goto(url, timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(wait)
    except Exception as e:  # noqa: BLE001
        print(f"  goto err: {type(e).__name__}: {str(e)[:100]}")
        return None
    try:
        print(f"  title={page.title()[:70]!r}")
        return page.content()
    except Exception:  # noqa: BLE001
        return None


def review_evidence(html, label):
    print(f"  --- {label} review evidence:")
    # headings / tabs mentioning reviews
    for m in re.finditer(r'>([^<>]{0,50}[Rr]eviews?[^<>]{0,50})<', html):
        txt = m.group(1).strip()
        if txt and "javascript" not in txt.lower():
            print(f"    text: {txt[:90]}")
    # json blobs mentioning review/pros/cons keys
    for key in ("pros", "cons", "review", "rating", "jobTitle",
                "job_title", "submittedAt", "createdAt"):
        c = len(re.findall(rf'"{key}"\s*:', html))
        if c:
            print(f'    json key "{key}": {c}')
    dates = sorted(set(re.findall(r"2026-\d{2}-\d{2}", html)))
    print(f"    2026 dates: {dates[:8]}")
    for kw in ("Makati", "Quezon City", "Taguig", "Manila", "Cebu"):
        c = html.count(kw)
        if c:
            print(f"    loc {kw!r}: {c}")


def main() -> int:
    profile = STORAGE / "browser_profile_c"
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(profile), channel="chrome", headless=True,
            viewport={"width": 1280, "height": 900}, locale="en-US",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"),
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # ---- KALIBRR: real company slug pages ----
        for url in ("https://www.kalibrr.com/c/aboitiz-power-corporation",
                    "https://www.kalibrr.com/c/accenture-philippines",
                    "https://www.kalibrr.com/c/globe-telecom"):
            html = goto(page, url)
            time.sleep(2)
            if not html:
                continue
            # collect links on the company page (tabs: jobs / reviews / about)
            try:
                hrefs = page.eval_on_selector_all(
                    "a[href]",
                    "els => els.map(e => e.getAttribute('href'))")
                tabs = sorted({h for h in hrefs
                               if h and re.search(r"/c/[^/]+/", h)})
                print(f"  sub-links: {tabs[:10]}")
            except Exception:  # noqa: BLE001
                pass
            review_evidence(html, "kalibrr")
            # try a /reviews sub-url explicitly
            time.sleep(2)
            html2 = goto(page, url.rstrip("/") + "/reviews", wait=5000)
            if html2:
                review_evidence(html2, "kalibrr /reviews")
            time.sleep(1)

        # ---- GLINTS: directory + first company ----
        html = goto(page, "https://glints.com/browse/company")
        time.sleep(2)
        company_urls = []
        if html:
            try:
                hrefs = page.eval_on_selector_all(
                    "a[href]",
                    "els => els.map(e => e.getAttribute('href'))")
                company_urls = sorted({h for h in hrefs
                                       if h and "/companies/" in h})
                print(f"  glints company urls: {len(company_urls)}; "
                      f"{company_urls[:5]}")
            except Exception:  # noqa: BLE001
                pass
        if company_urls:
            u = company_urls[0] if company_urls[0].startswith("http") \
                else "https://glints.com" + company_urls[0]
            time.sleep(2)
            html2 = goto(page, u)
            if html2:
                review_evidence(html2, "glints company")
                # sub-tabs
                try:
                    hrefs = page.eval_on_selector_all(
                        "a[href]",
                        "els => els.map(e => e.getAttribute('href'))")
                    tabs = sorted({h for h in hrefs if h and
                                   re.search(r"review|rating", h, re.I)})
                    print(f"  review tabs: {tabs[:6]}")
                except Exception:  # noqa: BLE001
                    pass

        ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
