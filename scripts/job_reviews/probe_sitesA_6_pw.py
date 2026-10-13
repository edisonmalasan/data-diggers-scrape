"""Site-group A probe 6: open a Monster company profile, look for reviews/ratings."""
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
STORAGE = HERE / ".storage"
STORAGE.mkdir(parents=True, exist_ok=True)

def main():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(locale="en-US")
        page = ctx.new_page()

        # 1) letter page -> pick first company profile link
        page.goto("https://www.monster.com/company/a", timeout=60000,
                  wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        hrefs = page.eval_on_selector_all(
            "a[href*='/company/']",
            "els => [...new Set(els.map(e => e.href))]")
        profs = [h for h in hrefs if re.search(r"/company/[a-z0-9-]+", h)
                 and not re.search(r"/company/[a-z]$", h)]
        print("profile links:", len(profs))
        for h in profs[:10]:
            print("   ", h)

        # 2) open one profile
        if profs:
            url = profs[0]
            print("== opening", url)
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(4500)
            print("title:", page.title()[:130])
            body = page.inner_text("body")
            low = body.lower()
            kws = ("review", "rating", "employee", "write a review", "pros", "cons",
                   "out of 5", "star")
            print("body len:", len(body), {k: low.count(k) for k in kws})
            (STORAGE / "tt_render_monster_profile.txt").write_text(
                body[:200000], encoding="utf-8")
            print("head:", " | ".join(body.split("\n")[:35])[:1000])
            dates = sorted(set(re.findall(
                r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+20\d\d",
                body)))
            print("dates:", dates[:10])
        browser.close()

if __name__ == "__main__":
    main()
