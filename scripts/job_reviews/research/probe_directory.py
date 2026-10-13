"""Check JobStreet robots.txt sitemaps + mine /companies directory for
company names with review counts (top-review companies = best yield)."""
import re
import requests
from playwright.sync_api import sync_playwright

# 1) robots.txt (try plain requests first; CF may allow it)
try:
    r = requests.get("https://ph.jobstreet.com/robots.txt",
                     headers={"User-Agent": "Mozilla/5.0 Chrome/126.0"}, timeout=30)
    print("robots status:", r.status_code)
    print(r.text[:1500])
except Exception as e:  # noqa: BLE001
    print("robots fetch failed:", e)

# 2) /companies directory — dump full text + company links
URL = "https://ph.jobstreet.com/companies"
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False)
    pg = b.new_context(locale="en-US").new_page()
    pg.goto(URL, timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    # scroll to bottom repeatedly to load everything
    for _ in range(6):
        pg.mouse.wheel(0, 6000)
        pg.wait_for_timeout(1200)
    txt = pg.evaluate("() => document.body.innerText")
    print("\n=== /companies page text (first 6000 chars) ===")
    print(txt[:6000])
    hrefs = pg.eval_on_selector_all(
        "a[href*='/companies/']", "els => els.map(e => e.getAttribute('href'))")
    uniq = sorted({h for h in hrefs if h})
    print(f"\n=== distinct /companies/ links: {len(uniq)} ===")
    for h in uniq[:80]:
        print(" ", h)
    # sitemap link inside page too?
    b.close()
