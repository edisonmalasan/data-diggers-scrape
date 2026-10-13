"""Probe an industry directory page: company links + pagination style."""
import re
from playwright.sync_api import sync_playwright

PAGES = [
    "https://ph.jobstreet.com/companies/directory/information-technology-services",
    "https://ph.jobstreet.com/companies/directory/computer-software-n-networking",
]

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False)
    pg = b.new_context(locale="en-US").new_page()
    for url in PAGES:
        pg.goto(url, timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(3500)
        for _ in range(3):
            pg.mouse.wheel(0, 5000)
            pg.wait_for_timeout(900)
        hrefs = pg.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))")
        comp = sorted({h.split("?")[0] for h in hrefs
                       if h and re.search(r"/companies/[a-z0-9\-]+$", h.split("?")[0])
                       and "/directory" not in h and "write-a-review" not in h})
        pagers = sorted({h for h in hrefs if h and re.search(r"page|directory/[a-z0-9\-]+/", h)})
        txt = pg.evaluate("() => document.body.innerText")
        print(f"\n=== {url}")
        print("company links:", len(comp))
        for h in comp[:40]:
            print("  ", h)
        print("pagination-ish:", pagers[:10])
        print("text head:", re.sub(r"\n+", " | ", txt)[:600])
    b.close()
