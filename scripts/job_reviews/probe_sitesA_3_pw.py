"""Site-group A probe 3: JS-rendered checks (talenttribe, jobsdb, monster, careerbuilder).

Headless Playwright, own profile dir. No logins, no CAPTCHA handling.
"""
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
STORAGE = HERE / ".storage"
PROFILE = STORAGE / "browser_profile_a"
STORAGE.mkdir(parents=True, exist_ok=True)

HOMEPAGES = {
    "talenttribe": "https://talenttribe.asia/",
    "tt_companies": "https://talenttribe.asia/companies",
    "tt_company": "https://talenttribe.asia/companies/shopee",
    "jobsdb_hk": "https://hk.jobsdb.com/",
    "monster": "https://www.monster.com/",
    "foundit_ph": "https://www.foundit.com.ph/",
    "careerbuilder": "https://www.careerbuilder.com/",
}

KW = ("review", "employee", "rating", "salary", "philippin", "manila", "cebu",
      "write a review", "pros", "cons")

def main(targets):
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception as e:
            print("chrome channel failed:", e, "-> falling back to bundled chromium")
            browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(locale="en-US", user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"))
        page = ctx.new_page()
        for name, url in targets.items():
            print("=" * 70)
            print(name, url)
            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)
                title = page.title()
                print("title:", title[:120])
                body = page.inner_text("body")
                low = body.lower()
                print("body len:", len(body), {k: low.count(k) for k in KW})
                # nav links that mention review/company
                links = page.eval_on_selector_all(
                    "a",
                    "els => els.map(e => (e.innerText||'').trim() + ' :: ' + e.href)"
                    ".filter(t => /review|company|employer|rating/i.test(t))")
                print("review-ish links:", len(links))
                for l in dict.fromkeys(links):
                    print("   ", l[:160])
                # dates present?
                dates = sorted(set(re.findall(
                    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+20\d\d",
                    body)))
                print("long dates:", dates[:12])
                iso = sorted(set(re.findall(r"\b202[4-6]-\d\d-\d\d\b", body)))
                print("iso dates:", iso[:12])
                # dump text for inspection
                (STORAGE / f"tt_render_{name}.txt").write_text(body[:200000], encoding="utf-8")
                print("head:", " | ".join(body.split("\n")[:25])[:800])
            except Exception as e:  # noqa: BLE001
                print("ERROR", type(e).__name__, e)
            time.sleep(2.5)
        browser.close()

if __name__ == "__main__":
    keys = sys.argv[1:] or list(HOMEPAGES)
    main({k: HOMEPAGES[k] for k in keys})
