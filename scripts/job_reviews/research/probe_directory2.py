"""Explore /companies/directory — full company index (path-based, robots-allowed)."""
import re
from playwright.sync_api import sync_playwright

BASE = "https://ph.jobstreet.com"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False)
    pg = b.new_context(locale="en-US").new_page()

    pg.goto(f"{BASE}/companies/directory", timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    for _ in range(4):
        pg.mouse.wheel(0, 5000)
        pg.wait_for_timeout(1000)
    txt = pg.evaluate("() => document.body.innerText")
    print("=== /companies/directory text (first 3500) ===")
    print(txt[:3500])

    hrefs = pg.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))")
    comp = sorted({h for h in hrefs if h and "/companies/" in h and "write-a-review" not in h})
    other = sorted({re.sub(r"\?.*", "", h or "") for h in hrefs
                    if h and "/companies" in h and h not in comp})
    print(f"\n=== company links: {len(comp)} ===")
    for h in comp[:60]:
        print(" ", h)
    print("\n=== other /companies paths ===")
    for h in other:
        print(" ", h)

    # letter / pagination links?
    letters = sorted({h for h in hrefs if h and re.search(r"/directory[/-]", h)})
    print("\n=== directory sub-paths ===")
    for h in letters[:60]:
        print(" ", h)
    b.close()
