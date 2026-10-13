"""Does ?sort.sortType=RD&sort.ascending=false change review ordering?

Probe 3 loads (same persistent profile as the live scraper):
  1. PLDT [Software Engineer]  — unsorted
  2. PLDT [Software Engineer]  — + RD sort
  3. Globe [Data Analyst]       — + RD sort
Print review dates/titles/locations for direct comparison.
"""
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parents[1]))
from playwright.sync_api import sync_playwright  # noqa: E402
from scrape_glassdoor_live import STORAGE, open_page  # noqa: E402

URLS = [
    ("PLDT SE plain",
     "https://www.glassdoor.com/Reviews/PLDT-Reviews-E522218.htm"
     "?filter.jobTitleExact=" + quote("Software Engineer")),
    ("PLDT SE sorted",
     "https://www.glassdoor.com/Reviews/PLDT-Reviews-E522218.htm"
     "?filter.jobTitleExact=" + quote("Software Engineer")
     + "&sort.sortType=RD&sort.ascending=false"),
    ("Globe DA sorted",
     "https://www.glassdoor.com/Reviews/Globe-Telecom-Reviews-E42313.htm"
     "?filter.jobTitleExact=" + quote("Data Analyst")
     + "&sort.sortType=RD&sort.ascending=false"),
]


def main() -> int:
    profile = STORAGE / "browser_profile"
    with sync_playwright() as p:
        def launch():
            c = p.chromium.launch_persistent_context(
                str(profile), channel="chrome", headless=False,
                viewport={"width": 1280, "height": 900}, locale="en-US",
                args=["--disable-blink-features=AutomationControlled"],
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/131.0.0.0 Safari/537.36"),
            )
            return c, (c.pages[0] if c.pages else c.new_page())

        ctx, page = launch()
        for label, url in URLS:
            status, revs = "crashed", []
            for attempt in range(3):
                try:
                    status, revs = open_page(page, url)
                except Exception as e:  # noqa: BLE001
                    print(f"  browser died ({type(e).__name__}); relaunch")
                    try:
                        ctx.close()
                    except Exception:  # noqa: BLE001
                        pass
                    import time
                    time.sleep(10)
                    ctx, page = launch()
                    status, revs = "crashed", []
                    continue
                if status == "ok":
                    break
                print(f"== {label}: status={status} — retry in 90s")
                import time
                time.sleep(90)
            print(f"== {label}: status={status} final_url={page.url[:110]}")
            for rev in revs:
                dt = (rev.get("reviewDateTime") or "")[:10]
                jt = ((rev.get("jobTitle") or {}).get("text") or "?")[:26]
                loc = ((rev.get("location") or {}).get("name") or "?")[:22]
                print(f"   {dt} | {jt} | {loc}")
        ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
