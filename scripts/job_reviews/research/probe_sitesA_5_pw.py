"""Site-group A probe 5: Monster company profile + foundit company page (JS render)."""
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parents[1]
STORAGE = HERE / ".storage"
STORAGE.mkdir(parents=True, exist_ok=True)

TARGETS = {
    "monster_company_hub": "https://www.monster.com/company/",
    "foundit_home": "https://www.foundit.com.ph/",
}

KW = ("review", "rating", "employee", "write a review", "pros", "cons", "testimonial")

def main():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(locale="en-US")
        page = ctx.new_page()
        for name, url in TARGETS.items():
            print("=" * 70)
            print(name, url)
            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(4500)
                print("title:", page.title()[:120])
                body = page.inner_text("body")
                low = body.lower()
                print("body len:", len(body), {k: low.count(k) for k in KW})
                links = page.eval_on_selector_all(
                    "a",
                    "els => els.map(e => (e.innerText||'').trim()+' :: '+e.href)"
                    ".filter(t => /company|employer|review/i.test(t))")
                print("company-ish links:", len(dict.fromkeys(links)))
                for l in list(dict.fromkeys(links))[:20]:
                    print("   ", l[:170])
                dates = sorted(set(re.findall(
                    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+20\d\d",
                    body)))
                print("dates:", dates[:10])
                (STORAGE / f"tt_render_{name}.txt").write_text(body[:200000], encoding="utf-8")
                print("head:", " | ".join(body.split("\n")[:20])[:700])
            except Exception as e:  # noqa: BLE001
                print("ERROR", type(e).__name__, e)
            time.sleep(2.5)
        browser.close()

if __name__ == "__main__":
    main()
