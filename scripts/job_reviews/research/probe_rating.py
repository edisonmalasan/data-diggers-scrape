"""Quick check: does filter.overallRating=THREE actually slice to rating 3?"""
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

STORAGE = Path(__file__).resolve().parents[1] / ".storage"
PROFILE = STORAGE / "browser_profile"
URL = ("https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138.htm"
       "?filter.overallRating=THREE")

CHALLENGE = ("Just a moment", "Security Check")


def extract(html):
    payload = "".join(re.findall(
        r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', html, re.S))
    payload = payload.replace('\\"', '"').replace("\\\\", "\\")
    i = payload.find('"reviews":[')
    if i < 0:
        return None
    arr, _ = json.JSONDecoder().raw_decode(payload[payload.index("[", i):])
    return arr


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
    page.goto(URL, timeout=45000, wait_until="domcontentloaded")
    deadline = time.time() + 50
    clicked = False
    result = None
    while time.time() < deadline:
        title = page.title()
        html = page.content()
        if any(c in title for c in CHALLENGE):
            if not clicked:
                for f in page.frames:
                    if "challenges.cloudflare.com" in f.url:
                        box = f.frame_element().bounding_box()
                        if box and box.get("width", 0) > 10:
                            page.mouse.click(box["x"] + 30,
                                             box["y"] + box["height"] / 2)
                            clicked = True
                            break
            page.wait_for_timeout(4000)
            continue
        result = extract(html)
        if result is not None:
            break
        page.wait_for_timeout(3000)
    ctx.close()

if result is None:
    print("RESULT: no payload (blocked?)")
else:
    print(f"RESULT: {len(result)} reviews")
    for r in result:
        print(f"  ratingOverall={r.get('ratingOverall')} "
              f"dt={r.get('reviewDateTime')} "
              f"loc={(r.get('location') or {}).get('name')!r}")
