"""Live probe v2: wait out JS challenges; detect when real content arrives."""
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

STORAGE = Path(__file__).resolve().parents[1] / ".storage"

TARGETS = [
    ("indeed", "https://ph.indeed.com/cmp/Accenture/reviews",
     'script[id="comp-initialData"]'),
    ("glassdoor", "https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138.htm",
     "div.ReviewCard"),
]

CHALLENGE_RE = re.compile(r"Just a moment|Verifying you are human|"
                          r"Checking your browser|Attention Required", re.I)


def wait_content(page, name, url, content_sel, patience=60):
    print(f"\n=== {name}: {url}")
    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
    except Exception as e:  # noqa: BLE001
        print(f"  goto: {e}")
    deadline = time.time() + patience
    while time.time() < deadline:
        try:
            title = page.title()
            html = page.content()
        except Exception:  # noqa: BLE001
            page.wait_for_timeout(2000)
            continue
        challenged = bool(CHALLENGE_RE.search(title) or CHALLENGE_RE.search(html[:60000]))
        try:
            n = page.locator(content_sel).count()
        except Exception:  # noqa: BLE001
            n = 0
        if n:
            (STORAGE / f"live_{name}.html").write_text(html, encoding="utf-8")
            print(f"  OK title={title!r} cards/sel={n} bytes={len(html)} "
                  f"after ~{int(patience - (deadline - time.time()))}s")
            return True
        print(f"  t+{int(patience - (deadline - time.time()))}s title={title!r} "
              f"challenge={challenged} bytes={len(html)}")
        page.wait_for_timeout(5000)
    # final dump for inspection
    try:
        html = page.content()
        (STORAGE / f"live_{name}_final.html").write_text(html, encoding="utf-8")
        print(f"  GAVE UP title={page.title()!r} bytes={len(html)} "
              f"-> live_{name}_final.html")
    except Exception as e:  # noqa: BLE001
        print(f"  GAVE UP ({e})")
    return False


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=False)
    ctx = browser.new_context(locale="en-US")
    page = ctx.new_page()
    ok_i = wait_content(page, *TARGETS[0])
    time.sleep(3)
    ok_g = wait_content(page, *TARGETS[1])
    browser.close()
print(f"\nRESULT indeed={'PASS' if ok_i else 'FAIL'} "
      f"glassdoor={'PASS' if ok_g else 'FAIL'}")
