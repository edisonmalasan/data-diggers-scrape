"""Site-group A probe 8: real CareerBuilder company profile + Monster letter page hrefs."""
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
STORAGE = HERE / ".storage"
STORAGE.mkdir(parents=True, exist_ok=True)

CB_PROFILE = "https://www.careerbuilder.com/company/804-technology/C310GH6PKQG5XKRNCQ8"

def inspect(page, name, url, extra_kw=("review", "rating", "employee", "pros", "cons",
                                       "out of 5", "write a review", "star")):
    print("=" * 70)
    print(name, url)
    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(4500)
        print("title:", page.title()[:130])
        body = page.inner_text("body")
        low = body.lower()
        print("body len:", len(body), {k: low.count(k) for k in extra_kw})
        dates = sorted(set(re.findall(
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+20\d\d",
            body)))
        print("dates:", dates[:10])
        (STORAGE / f"tt_render_{name}.txt").write_text(body[:200000], encoding="utf-8")
        print("head:", " | ".join(body.split("\n")[:30])[:900])
        return body
    except Exception as e:  # noqa: BLE001
        print("ERROR", type(e).__name__, e)
        return ""

def main():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(locale="en-US")
        page = ctx.new_page()

        inspect(page, "cb_profile", CB_PROFILE)

        inspect(page, "monster_letter_a", "https://www.monster.com/company/a")
        hrefs = page.eval_on_selector_all(
            "a", "els => [...new Set(els.map(e => e.href))]")
        comp = [h for h in hrefs if "/company/" in h]
        print("monster /company/ hrefs:", len(comp))
        for h in comp[:30]:
            print("   ", h)
        browser.close()

if __name__ == "__main__":
    main()
