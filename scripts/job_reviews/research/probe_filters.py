"""List all filter/sub-paths JobStreet exposes on a company reviews page."""
from playwright.sync_api import sync_playwright

URL = "https://ph.jobstreet.com/companies/accenture-168430182370928/reviews"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False)
    pg = b.new_context(locale="en-US").new_page()
    pg.goto(URL, timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_function("document.body.innerText.includes('The good things')",
                         timeout=15000)
    pg.wait_for_timeout(1500)
    hrefs = pg.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))")
    rev = sorted({h for h in hrefs if h and "/reviews" in h})
    print("--- hrefs containing /reviews ---")
    for h in rev:
        print(" ", h)
    # any filter controls (buttons/selects) on the page?
    print("--- filter-ish UI text ---")
    txts = pg.eval_on_selector_all(
        "button, [role='tab'], select, summary",
        "els => els.map(e => (e.innerText||'').trim()).filter(Boolean)")
    for t in sorted(set(txts))[:40]:
        print(" ", t)
    b.close()
