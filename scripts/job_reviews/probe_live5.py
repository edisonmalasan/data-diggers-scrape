"""Live probe v5: Glassdoor pagination + sort + Manila index + jobTitle filter.

Reuses the Turnstile widget click from v4. Answers:
  Q1 does _P2 pagination render more anonymous reviews?
  Q2 does sort.sortType=RD (review date desc) apply?
  Q3 does the Manila location-index page work?
  Q4 does filter.jobTitleExact narrow reviews?
"""
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

STORAGE = Path(__file__).resolve().parent / ".storage"
PROFILE = STORAGE / "browser_profile"

CHALLENGE = ("Just a moment", "Verifying you are human", "Security Check",
             "Attention Required")


def extract_reviews(html: str) -> list[dict]:
    payload = "".join(re.findall(
        r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', html, re.S))
    payload = payload.replace('\\"', '"').replace("\\\\", "\\")
    i = payload.find('"reviews":[')
    if i < 0:
        return []
    start = payload.index("[", i)
    try:
        arr, _ = json.JSONDecoder().raw_decode(payload[start:])
    except Exception:  # noqa: BLE001
        return []
    return arr if isinstance(arr, list) else []


def click_widget(page) -> bool:
    for f in page.frames:
        if "challenges.cloudflare.com" not in f.url:
            continue
        try:
            box = f.frame_element().bounding_box()
        except Exception:  # noqa: BLE001
            continue
        if box and box.get("width", 0) > 10:
            page.mouse.click(box["x"] + 30, box["y"] + box["height"] / 2)
            return True
    return False


def fetch(page, url, patience=60):
    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
    except Exception as e:  # noqa: BLE001
        print("  goto err:", e)
    deadline = time.time() + patience
    clicked = False
    while time.time() < deadline:
        try:
            title = page.title()
            html = page.content()
        except Exception:  # noqa: BLE001
            page.wait_for_timeout(2000)
            continue
        challenged = any(c in title for c in CHALLENGE)
        if not challenged and '"reviews":[' in html.replace('\\"', '"'):
            return title, html
        if challenged and not clicked:
            clicked = click_widget(page)
        page.wait_for_timeout(4000)
    return None, html


TESTS = [
    ("p1_default", "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138.htm"),
    ("p2_paged",
     "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138_P2.htm"),
    ("sort_date",
     "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138.htm"
     "?sort.sortType=RD&sort.ascending=false"),
    ("manila_index",
     "https://www.glassdoor.com/Reviews/Manila-Reviews-EI_IE1196434_IL.0,6.htm"),
    ("jobtitle_filter",
     "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138.htm"
     "?filter.jobTitleExact=Software+Engineer"),
]

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        str(PROFILE), channel="chrome", headless=False,
        viewport={"width": 1280, "height": 900}, locale="en-US",
        args=["--disable-blink-features=AutomationControlled"],
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"),
    )
    ctx.add_init_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        "window.chrome={runtime:{}};"
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    out = {}
    for name, url in TESTS:
        print(f"\n=== {name}: {url}")
        title, html = fetch(page, url)
        if title is None:
            print("  BLOCKED/timeout")
            out[name] = None
            continue
        revs = extract_reviews(html)
        print(f"  title={title[:80]!r}")
        print(f"  reviews={len(revs)}")
        for r in revs:
            jt = (r.get("jobTitle") or {}).get("text")
            loc = (r.get("location") or {})
            print(f"    id={r.get('reviewId')} dt={r.get('reviewDateTime')} "
                  f"job={jt!r} loc={loc.get('name')!r}/{loc.get('type')} "
                  f"rating={r.get('ratingOverall')}")
        out[name] = {"title": title, "n": len(revs)}
        (STORAGE / f"gd5_{name}.html").write_text(html, encoding="utf-8")
        time.sleep(3)
    ctx.close()

print("\nSUMMARY:", json.dumps(out, indent=1))
