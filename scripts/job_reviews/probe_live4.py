"""Live probe v4: click the Turnstile widget (cType=interactive) inside the
challenge iframe, then verify real content loads. Persistent profile keeps any
clearance cookie for later scraping runs."""
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

STORAGE = Path(__file__).resolve().parent / ".storage"
PROFILE = STORAGE / "browser_profile"

TARGETS = [
    ("indeed", "https://ph.indeed.com/cmp/Accenture/reviews",
     'script[id="comp-initialData"]'),
    ("glassdoor", "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138.htm",
     "div.ReviewCard"),
]

CHALLENGE = ("Just a moment", "Verifying you are human", "Security Check",
             "Attention Required")


def click_widget(page) -> bool:
    """Find a Cloudflare challenge iframe and click its checkbox area."""
    for f in page.frames:
        if "challenges.cloudflare.com" not in f.url and "cdn-cgi" not in f.url:
            continue
        try:
            el = f.frame_element()
            box = el.bounding_box()
        except Exception:  # noqa: BLE001
            continue
        if not box or box.get("width", 0) < 10:
            continue
        # checkbox sits near the left edge, vertically centered
        x = box["x"] + 30
        y = box["y"] + box["height"] / 2
        print(f"  clicking widget @ ({x:.0f},{y:.0f}) "
              f"box={box['width']:.0f}x{box['height']:.0f}")
        page.mouse.move(x - 60, y + 40, steps=8)
        page.wait_for_timeout(300)
        page.mouse.click(x, y)
        return True
    # fallback: any iframe on the page
    for sel in ("iframe", "div#bstyI3 iframe"):
        try:
            loc = page.locator(sel)
            if loc.count():
                box = loc.first.bounding_box()
                if box and box.get("width", 0) > 20:
                    print(f"  fallback click on {sel}")
                    page.mouse.click(box["x"] + 30, box["y"] + box["height"] / 2)
                    return True
        except Exception:  # noqa: BLE001
            pass
    return False


def run(page, name, url, sel, patience=75):
    print(f"\n=== {name}")
    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
    except Exception as e:  # noqa: BLE001
        print("  goto:", e)
    deadline = time.time() + patience
    clicked = False
    last_title = ""
    while time.time() < deadline:
        try:
            title = page.title()
            n = page.locator(sel).count()
        except Exception:  # noqa: BLE001
            page.wait_for_timeout(2000)
            continue
        if n:
            html = page.content()
            (STORAGE / f"live4_{name}.html").write_text(html, encoding="utf-8")
            print(f"  PASS title={title!r} sel={n} bytes={len(html)}")
            return True
        challenged = any(c in title for c in CHALLENGE)
        if challenged and not clicked:
            clicked = click_widget(page)
        elif challenged and clicked and title != last_title:
            clicked = False  # title changed -> widget may need a second round
        last_title = title
        print(f"  t+{patience - int(deadline - time.time())}s "
              f"title={title!r} challenge={challenged}")
        page.wait_for_timeout(4000)
    try:
        html = page.content()
        (STORAGE / f"live4_{name}_final.html").write_text(html, encoding="utf-8")
        print(f"  FAIL title={page.title()!r} -> live4_{name}_final.html")
    except Exception as e:  # noqa: BLE001
        print("  FAIL", e)
    return False


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
    results = {}
    for t in TARGETS:
        results[t[0]] = run(page, *t)
        time.sleep(4)
    ctx.close()
print("\nRESULT:", {k: ("PASS" if v else "FAIL") for k, v in results.items()})
