"""One-time login per site. Saves a session file the scraper reuses.

Chrome locks its live profile, so automation cannot borrow it directly
(that TimeoutError you hit). Instead: this opens a FRESH Playwright browser,
you log in once by hand, it saves a session cookie file.

  python scripts/job_reviews/login.py --site indeed
  python scripts/job_reviews/login.py --site glassdoor
  python scripts/job_reviews/login.py --site jobstreet
  python scripts/job_reviews/login.py --site linkedin

Then: python scripts/job_reviews/collect.py --check
"""

from __future__ import annotations

import argparse
from pathlib import Path

STORAGE_DIR = Path(__file__).with_name(".storage")
HOMEPAGES = {
    "indeed": "https://ph.indeed.com/",
    "glassdoor": "https://www.glassdoor.com/",
    "jobstreet": "https://www.jobstreet.com.ph/",
    "linkedin": "https://www.linkedin.com/login",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, choices=list(HOMEPAGES))
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    STORAGE_DIR.mkdir(exist_ok=True)
    out = STORAGE_DIR / f"{args.site}.json"
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(HOMEPAGES[args.site], timeout=60000)
        print(f"\nLog in to {args.site} in the opened window.")
        input("Press ENTER here when you are logged in ... ")
        ctx.storage_state(path=str(out))
        browser.close()
    print(f"Saved session -> {out}")
    print("Next: python scripts/job_reviews/collect.py --check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
