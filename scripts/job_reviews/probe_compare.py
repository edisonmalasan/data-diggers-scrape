"""Diagnose: are ?filter.jobTitleExact / ?filter.overallRating honored?

For a few URL variants prints the FINAL url after redirects, page title,
and the (reviewId, jobTitle.text, location, dt) of each returned review.
Base vs filtered reviewIds compared -> identical means filter was dropped.
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

STORAGE = Path(__file__).resolve().parent / ".storage"
PROFILE = STORAGE / "browser_profile"
CHALLENGE = ("Just a moment", "Security Check", "Verifying you are human")

CASES = [
    ("TP-PH base",
     "https://www.glassdoor.com/Reviews/Teleperformance-Philippines-Reviews-E348159.htm"),
    ("TP-PH sw-eng",
     "https://www.glassdoor.com/Reviews/Teleperformance-Philippines-Reviews-E348159.htm"
     "?filter.jobTitleExact=" + quote("Software Engineer")),
    ("TP-global sw-eng",
     "https://www.glassdoor.com/Reviews/Teleperformance-Reviews-E9779.htm"
     "?filter.jobTitleExact=" + quote("Software Engineer")),
    ("Accenture sw-eng (control)",
     "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138.htm"
     "?filter.jobTitleExact=" + quote("Software Engineer")),
    ("Globe sw-eng",
     "https://www.glassdoor.com/Reviews/Globe-Telecom-Reviews-E42313.htm"
     "?filter.jobTitleExact=" + quote("Software Engineer")),
]


def extract(html):
    payload = "".join(re.findall(
        r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', html, re.S))
    payload = payload.replace('\\"', '"').replace("\\\\", "\\")
    i = payload.find('"reviews":[')
    if i < 0:
        return None
    arr, _ = json.JSONDecoder().raw_decode(payload[payload.index("[", i):])
    return arr


def open_case(page, url, patience=50):
    try:
        page.goto(url, timeout=45000, wait_until="domcontentloaded")
    except Exception as e:  # noqa: BLE001
        print(f"    goto err: {e}")
    deadline = time.time() + patience
    clicked = 0
    while time.time() < deadline:
        try:
            title = page.title()
            html = page.content()
        except Exception:  # noqa: BLE001
            page.wait_for_timeout(1500)
            continue
        challenged = any(c in title for c in CHALLENGE)
        if not challenged:
            revs = extract(html)
            if revs is not None:
                return page.url, title, revs
        elif clicked < 3:
            for f in page.frames:
                if "challenges.cloudflare.com" in f.url:
                    box = f.frame_element().bounding_box()
                    if box and box.get("width", 0) > 10:
                        page.mouse.click(box["x"] + 30,
                                         box["y"] + box["height"] / 2)
                        clicked += 1
                        break
        page.wait_for_timeout(3500)
    return page.url, "(no payload)", None


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
    for label, url in CASES:
        final_url, title, revs = open_case(page, url)
        print(f"\n=== {label}")
        print(f"    requested: ...{url[-95:]}")
        print(f"    final    : ...{final_url[-95:]}")
        print(f"    pagetitle: {title[:80]}")
        if revs is None:
            print("    reviews : NO PAYLOAD")
        else:
            for r in revs:
                jt = (r.get("jobTitle") or {}).get("text")
                loc = (r.get("location") or {}).get("name")
                print(f"      id={r.get('reviewId')} title={jt!r} "
                      f"loc={loc!r} dt={(r.get('reviewDateTime') or '')[:10]} "
                      f"rating={r.get('ratingOverall')}")
        time.sleep(3.5)
    ctx.close()
