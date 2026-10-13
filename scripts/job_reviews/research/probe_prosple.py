"""Deep probe: Prosple PH graduate-employer review pages (alive per round 3).

Contract questions per review: date? job title? location? text? And corpus
structure: how to enumerate companies, pagination, tech-employer presence.
Own headless profile, no login.
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from playwright.sync_api import sync_playwright  # noqa: E402

STORAGE = Path(__file__).parents[1] / ".storage"
TOPICS = ("training", "culture", "pay", "progression", "work-life-balance")
PH_TECH = ("accenture", "globe-telecom", "globe", "smart-communications",
           "pldt", "sykes", "everise", "microsourcing", "asticom",
           "shopee", "lazada")


def dump(page, url, label, wait=7000):
    print(f"\n=== [{label}] {url}")
    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(wait)
    except Exception as e:  # noqa: BLE001
        print(f"  goto err: {type(e).__name__}: {str(e)[:110]}")
        return None
    try:
        title = page.title()
    except Exception:  # noqa: BLE001
        title = "?"
    print(f"  title={title[:90]!r}")
    if "Just a moment" in title or "One moment" in title:
        print("  (challenge page — waiting 15s more)")
        page.wait_for_timeout(15000)
        try:
            title = page.title()
            print(f"  title now={title[:90]!r}")
        except Exception:  # noqa: BLE001
            pass
    try:
        html = page.content()
    except Exception:  # noqa: BLE001
        return None

    # contract-field evidence
    for kw in ("2026", "2025", "2024", "Reviewed", "reviewed on", "Pros",
               "Cons", "Job Title", "job title", "Current job", "Course",
               "University", "Makati", "Quezon City", "Taguig", "Manila",
               "Cebu", "Philippines", "Anonymous"):
        c = html.count(kw)
        if c:
            print(f"  kw {kw!r}: {c}")
    dates = sorted(set(re.findall(r"20(?:2[3-6])-\d{2}-\d{2}", html)))
    print("  iso dates:", dates[:12])
    dates2 = sorted(set(re.findall(
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* "
        r"\d{1,2},?\s*20(?:2[3-6])", html)))
    print("  textual dates:", dates2[:12])

    # visible review blocks
    try:
        blocks = page.eval_on_selector_all(
            "p, li, blockquote, article div",
            """els => els.map(e => e.innerText)
                .filter(t => t && t.trim().length > 60)
                .slice(0, 10)""")
        for b in blocks:
            print("  block:", b[:160].replace("\n", " | "))
    except Exception:  # noqa: BLE001
        pass

    # links: pagination + other companies/topics
    try:
        hrefs = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => e.getAttribute('href'))")
        rev = sorted({h for h in hrefs if h and "/reviews/" in h})
        emp = sorted({h for h in hrefs if h and "/graduate-employers/" in h})
        page_links = sorted({h for h in hrefs if h and "page=" in h})
        print(f"  /reviews/ links: {len(rev)}; sample {rev[:5]}")
        print(f"  employer links: {len(emp)}; sample {emp[:5]}")
        print(f"  pagination links: {page_links[:5]}")
    except Exception:  # noqa: BLE001
        pass
    return html


def main() -> int:
    profile = STORAGE / "browser_profile_c"
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(profile), channel="chrome", headless=True,
            viewport={"width": 1280, "height": 900}, locale="en-US",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"),
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # 1. the known review page, full evidence
        dump(page, "https://ph.prosple.com/graduate-employers/"
                   "emma-the-sleep-company/reviews/training", "emma training")
        time.sleep(2)

        # 2. same company, other topic (does one review span topics?)
        dump(page, "https://ph.prosple.com/graduate-employers/"
                   "emma-the-sleep-company/reviews/culture", "emma culture")
        time.sleep(2)

        # 3. employer directory — enumeration path
        dump(page, "https://ph.prosple.com/graduate-employers", "directory",
             wait=8000)
        time.sleep(2)

        # 4. a big PH tech employer — accenture
        dump(page, "https://ph.prosple.com/graduate-employers/accenture",
             "accenture profile")
        time.sleep(2)
        dump(page, "https://ph.prosple.com/graduate-employers/accenture/"
                   "reviews/training", "accenture reviews")
        time.sleep(2)

        # 5. robots via browser (requests may 403)
        try:
            page.goto("https://ph.prosple.com/robots.txt",
                      timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            txt = page.inner_text("body")[:500]
            print("\n=== robots.txt:\n", txt)
        except Exception as e:  # noqa: BLE001
            print(f"\n=== robots err: {type(e).__name__}")

        ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
