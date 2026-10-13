"""Round 3: JobTopGun (requests) + Prosple PH review pages (browser).

New leads from websearch. Evidence-only: review corpus? contract fields?
2026 PH CS/IT examples? No login, own headless profile for Playwright.
"""
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parents[1]))
from playwright.sync_api import sync_playwright  # noqa: E402

STORAGE = Path(__file__).parents[1] / ".storage"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/131.0.0.0 Safari/537.36"}


def req(u):
    try:
        r = requests.get(u, headers=H, timeout=30)
        print(f"GET {u} -> {r.status_code} len={len(r.text)}")
        return r
    except Exception as e:  # noqa: BLE001
        print(f"GET {u} ERR {type(e).__name__}: {str(e)[:80]}")
        return None


def jobtopgun():
    print("\n########## JOBTOPGUN ##########")
    for u in ("https://www.jobtopgun.com/robots.txt",
              "https://www.jobtopgun.co.th/robots.txt",
              "https://jobtopgun.com/robots.txt"):
        r = req(u)
        time.sleep(2)
        if r is not None and r.ok:
            print(r.text[:300])
            break
    for u in ("https://www.jobtopgun.com/", "https://www.jobtopgun.co.th/"):
        r = req(u)
        time.sleep(2)
        if r is not None and r.ok and "One moment" not in r.text[:300]:
            t = r.text
            m = re.search(r"<title[^>]*>(.*?)</title>", t, re.S)
            print("title:", (m.group(1) if m else "?")[:90])
            for kw in ("Philippines", "Makati", "review", "Review", "2026",
                       "รีวิว", "Thailand"):
                print(f"  kw {kw!r}:", t.count(kw))
            hrefs = sorted(set(re.findall(r'href="(/[^"]{2,60})"', t)))
            print("  reviewish:", [h for h in hrefs
                                   if re.search(r"review|company", h, re.I)]
                  [:12])
            break


def prosple():
    print("\n########## PROSPLE PH ##########")
    urls = ("https://ph.prosple.com/graduate-employers/"
            "emma-the-sleep-company/reviews/training",
            "https://ph.prosple.com/graduate-employers")
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
        for u in urls:
            print(f"\n=== {u}")
            try:
                page.goto(u, timeout=45000, wait_until="domcontentloaded")
                page.wait_for_timeout(6000)
                html = page.content()
                print(f"  title={page.title()[:80]!r}")
            except Exception as e:  # noqa: BLE001
                print(f"  goto err: {type(e).__name__}: {str(e)[:100]}")
                continue
            # review-text blocks + fields
            for kw in ("review", "Review", "2026", "2025", "Pros", "Cons",
                       "Job Title", "jobTitle", "Course", "University",
                       "Makati", "Quezon City", "Philippines"):
                c = html.count(kw)
                if c:
                    print(f"  kw {kw!r}: {c}")
            dates = sorted(set(re.findall(r"20(?:2[456])-\d{2}-\d{2}", html)))
            print("  iso dates:", dates[:10])
            # visible review headings
            try:
                txt = page.eval_on_selector_all(
                    "h1,h2,h3,h4,blockquote,p",
                    "els => els.map(e => e.innerText).filter(t => t && "
                    "t.length > 40).slice(0, 6)")
                for t in txt:
                    print("  block:", t[:120].replace("\n", " | "))
            except Exception:  # noqa: BLE001
                pass
            # company/review links
            try:
                hrefs = page.eval_on_selector_all(
                    "a[href]",
                    "els => els.map(e => e.getAttribute('href'))")
                rev = sorted({h for h in hrefs if h and "/reviews" in h})
                print(f"  review links: {len(rev)}; {rev[:6]}")
            except Exception:  # noqa: BLE001
                pass
            time.sleep(2)
        ctx.close()


def main() -> int:
    jobtopgun()
    prosple()
    return 0


if __name__ == "__main__":
    sys.exit(main())
