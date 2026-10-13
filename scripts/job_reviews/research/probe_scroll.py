"""Does JobStreet /reviews lazy-load more reviews on scroll (same URL = robots-OK)?"""
from playwright.sync_api import sync_playwright

URL = "https://ph.jobstreet.com/companies/accenture-168430182370928/reviews"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False)
    pg = b.new_context(locale="en-US").new_page()
    pg.goto(URL, timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_function("document.body.innerText.includes('The good things')", timeout=15000)
    pg.wait_for_timeout(1500)

    def count():
        return pg.evaluate("() => [...document.querySelectorAll('span,div')]"
                           ".filter(e => (e.innerText||'').trim()==='The good things').length")

    print("initial labels:", count())
    for i in range(8):
        pg.mouse.wheel(0, 6000)
        pg.wait_for_timeout(1800)
        c = count()
        print(f"scroll {i+1}: labels={c}")
    # check for pagination links (query-string links we must NOT follow per robots)
    hrefs = pg.eval_on_selector_all("a[href*='page']", "els => els.map(e => e.getAttribute('href'))")
    print("page links:", hrefs[:8])
    b.close()
