"""Live probe v3: anti-detection stealth (persistent profile, masked webdriver)."""
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

STORAGE = Path(__file__).resolve().parents[1] / ".storage"
PROFILE = STORAGE / "browser_profile"

INIT_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = {runtime: {}};
const origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (params) =>
  (params.name === 'notifications'
    ? Promise.resolve({state: Notification.permission})
    : origQuery(params));
"""

TARGETS = [
    ("indeed", "https://ph.indeed.com/cmp/Accenture/reviews",
     'script[id="comp-initialData"]'),
    ("glassdoor", "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138.htm",
     "div.ReviewCard"),
]

CHALLENGE = ("Just a moment", "Verifying you are human", "Security Check",
             "Attention Required")


def run(page, name, url, sel, patience=75):
    print(f"\n=== {name}")
    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
    except Exception as e:  # noqa: BLE001
        print("  goto:", e)
    deadline = time.time() + patience
    while time.time() < deadline:
        try:
            title = page.title()
            n = page.locator(sel).count()
        except Exception:  # noqa: BLE001
            page.wait_for_timeout(2000)
            continue
        if n:
            html = page.content()
            (STORAGE / f"live3_{name}.html").write_text(html, encoding="utf-8")
            print(f"  PASS title={title!r} sel={n} bytes={len(html)}")
            return True
        challenged = any(c in title for c in CHALLENGE)
        # human-like behavior while waiting
        try:
            page.mouse.wheel(0, 300)
        except Exception:  # noqa: BLE001
            pass
        print(f"  t+{patience - int(deadline - time.time())}s "
              f"title={title!r} challenge={challenged}")
        page.wait_for_timeout(5000)
    try:
        html = page.content()
        (STORAGE / f"live3_{name}_final.html").write_text(html, encoding="utf-8")
        print(f"  FAIL title={page.title()!r} -> live3_{name}_final.html")
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
    ctx.add_init_script(INIT_JS)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    results = {}
    for t in TARGETS:
        results[t[0]] = run(page, *t)
        time.sleep(4)
    ctx.close()
print("\nRESULT:", {k: ("PASS" if v else "FAIL") for k, v in results.items()})
