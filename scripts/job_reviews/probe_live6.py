"""Live probe v6: diagnose _P2 + Manila index; test location filter params.

Always saves the final HTML and reports challenge vs login-wall vs reviews.
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
LOGIN_MARK = ("Sign in to continue", "Create an account", "Log in to see",
              "please sign in", "Sign in to view", "Continue with Google")


def extract_reviews(html):
    payload = "".join(re.findall(
        r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', html, re.S))
    payload = payload.replace('\\"', '"').replace("\\\\", "\\")
    i = payload.find('"reviews":[')
    if i < 0:
        return []
    try:
        arr, _ = json.JSONDecoder().raw_decode(payload[payload.index("[", i):])
        return arr or []
    except Exception:  # noqa: BLE001
        return []


def click_widget(page):
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


def fetch(page, url, patience=50):
    try:
        page.goto(url, timeout=45000, wait_until="domcontentloaded")
    except Exception as e:  # noqa: BLE001
        print("  goto err:", e)
    deadline = time.time() + patience
    clicked = 0
    html = ""
    while time.time() < deadline:
        try:
            title = page.title()
            html = page.content()
        except Exception:  # noqa: BLE001
            page.wait_for_timeout(1500)
            continue
        challenged = any(c in title for c in CHALLENGE)
        if not challenged:
            revs = extract_reviews(html)
            if revs:
                return title, html, revs, "ok"
            low = html[:400000]
            login = any(m.lower() in low.lower() for m in LOGIN_MARK)
            if login:
                return title, html, [], "login-wall?"
        if challenged and clicked < 3:
            if click_widget(page):
                clicked += 1
        page.wait_for_timeout(4000)
    title = ""
    try:
        title = page.title()
    except Exception:  # noqa: BLE001
        pass
    return title, html, [], "timeout"


TESTS = [
    ("p2", "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138_P2.htm"),
    ("manila",
     "https://www.glassdoor.com/Reviews/Manila-Reviews-EI_IE1196434_IL.0,6.htm"),
    ("loc_city",
     "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138.htm"
     "?filter.city=Manila"),
    ("loc_default",
     "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138.htm"
     "?filter.defaultLocation=Manila"),
    ("loc_locid",
     "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138.htm"
     "?locId=1196434&locType=2"),
]

summary = {}
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
    for name, url in TESTS:
        print(f"\n=== {name}")
        title, html, revs, status = fetch(page, url)
        (STORAGE / f"gd6_{name}.html").write_text(html or "",
                                                   encoding="utf-8")
        locs = [((r.get("location") or {}).get("name"),
                 (r.get("jobTitle") or {}).get("text")) for r in revs]
        print(f"  status={status} title={title[:70]!r}")
        print(f"  reviews={len(revs)} loc/job={locs}")
        summary[name] = {"status": status, "n": len(revs)}
        time.sleep(3)
    ctx.close()

print("\nSUMMARY:", json.dumps(summary, indent=1))
