"""Browser-probe Kalibrr + Glints (requests-only attempts failed: JS shell / 403).

Own headless profile (browser_profile_c) — never touches the Glassdoor profile.
No login, no CAPTCHA solving. Evidence-only: does a review corpus exist, which
contract fields, any 2026 dates?
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from playwright.sync_api import sync_playwright  # noqa: E402

STORAGE = Path(__file__).parent / ".storage"
KW = ("review", "Review", "2026", "Pros", "Cons", "rating", "Rating",
      "Makati", "Quezon City", "Philippines", "jobTitle", "Job Title")


def scan(page, label, url, extra_links=None):
    print(f"\n=== {label}: {url}")
    try:
        page.goto(url, timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
    except Exception as e:  # noqa: BLE001
        print(f"  goto err: {type(e).__name__}: {str(e)[:120]}")
        return
    try:
        title = page.title()
    except Exception:  # noqa: BLE001
        title = "?"
    print(f"  title={title[:80]!r} url={page.url[:100]}")
    try:
        html = page.content()
    except Exception:  # noqa: BLE001
        return
    for kw in KW:
        c = html.count(kw)
        if c:
            print(f"    {kw!r}: {c}")
    # find review-ish links in rendered DOM
    try:
        hrefs = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => e.getAttribute('href')).filter(Boolean)")
    except Exception:  # noqa: BLE001
        hrefs = []
    hits = sorted({h for h in hrefs
                   if re.search(r"review|compan|employer", h or "", re.I)})
    print(f"  reviewish links: {len(hits)}; sample: {hits[:8]}")
    if extra_links:
        for pat, label2 in extra_links:
            m = [h for h in hrefs if re.search(pat, h or "", re.I)]
            if m:
                print(f"  {label2}: {m[:5]}")
    dates = sorted(set(re.findall(r"20(?:25|26)-\d{2}-\d{2}", html)))
    print(f"  recent iso dates: {dates[:8]}")


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

        # --- Kalibrr ---
        scan(page, "kalibrr companies dir",
             "https://www.kalibrr.com/home/companies",
             extra_links=[(r"/home/company/", "company links")])
        time.sleep(2)
        try:
            hrefs = page.eval_on_selector_all(
                "a[href]",
                "els => els.map(e => e.getAttribute('href'))")
            comp = [h for h in hrefs if "/home/company/" in (h or "")]
            if comp:
                c0 = comp[0] if comp[0].startswith("http") \
                    else "https://www.kalibrr.com" + comp[0]
                scan(page, "kalibrr company page", c0)
            else:
                # direct guess of a big PH employer
                scan(page, "kalibrr company page (direct)",
                     "https://www.kalibrr.com/home/company/accenture-philippines")
        except Exception as e:  # noqa: BLE001
            print(f"  link collect err: {e}")
        time.sleep(2)

        # --- Glints ---
        scan(page, "glints PH home", "https://glints.com/ph/en",
             extra_links=[(r"/compan|/employ", "company/employer links")])
        time.sleep(2)
        try:
            hrefs = page.eval_on_selector_all(
                "a[href]",
                "els => els.map(e => e.getAttribute('href'))")
            comp = [h for h in hrefs
                    if re.search(r"/compan|/employ", h or "", re.I)]
            if comp:
                g0 = comp[0] if comp[0].startswith("http") \
                    else "https://glints.com" + comp[0]
                scan(page, "glints company page", g0)
        except Exception as e:  # noqa: BLE001
            print(f"  link collect err: {e}")
        time.sleep(2)

        # --- Bossjob ---
        scan(page, "bossjob home", "https://bossjob.ph/",
             extra_links=[(r"/compan|/employer|/profile", "company links")])

        ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
