"""Phase 6: fishbowl post/company metadata + thelayoff thread retry + blind headed try."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from siteb_lib import STORAGE, UA  # noqa: E402

PROFILE = STORAGE / "browser_profile_disc"


def snap(page, name: str) -> str:
    html = page.content()
    (STORAGE / f"pw_{name}.html").write_text(html, encoding="utf-8")
    m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    print(f"--- {name}: url={page.url} title={(m.group(1).strip() if m else '?')[:90]!r}",
          flush=True)
    return html


def main() -> int:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), channel="chrome", headless=True, locale="en-US",
            user_agent=UA, viewport={"width": 1366, "height": 900},
        )
        page = ctx.new_page()

        def go(url: str, wait: int = 4000) -> None:
            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
            except Exception as e:  # noqa: BLE001
                print(f"    goto ERR {type(e).__name__} {e}", flush=True)
            page.wait_for_timeout(wait)

        # 1) fishbowl single post
        go("https://www.fishbowlapp.com/post/accenture-specialist-career-level-9-what-does-this-mean-in-terms-of-compensation", 5000)
        h = snap(page, "fb_post1")
        txt = page.inner_text("body")
        (STORAGE / "pw_fb_post1.txt").write_text(txt, encoding="utf-8")
        print("    post1 body[:700]:", repr(txt[:700]), flush=True)
        dts = sorted(set(re.findall(r"\b20\d{2}-\d{2}-\d{2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+20\d{2}\b", h)))
        print("    post1 dates:", dts[:10], flush=True)

        # 2) fishbowl company page
        go("https://www.fishbowlapp.com/company/accenture", 5000)
        hc = snap(page, "fb_company")
        txtc = page.inner_text("body")
        (STORAGE / "pw_fb_company.txt").write_text(txtc, encoding="utf-8")
        print("    company body[:700]:", repr(txtc[:700]), flush=True)
        post_links = sorted(set(re.findall(r'href="(/post/[^"]+)"', hc)))
        print("    company->post links:", len(post_links), post_links[:5], flush=True)

        # 3) thelayoff thread retry (longer settle for Cloudflare auto-verify)
        for attempt, wait in enumerate((15000, 20000), 1):
            go("https://www.thelayoff.com/t/1m2fyv8aq", wait)
            h3 = snap(page, f"layoff_thread1_try{attempt}")
            if "Just a moment" not in h3 and "security verification" not in h3[:2000]:
                t3 = page.inner_text("body")
                (STORAGE / "pw_layoff_thread1.txt").write_text(t3, encoding="utf-8")
                print("    thread body[:700]:", repr(t3[:700]), flush=True)
                break
            print(f"    try{attempt}: still on Cloudflare", flush=True)

        ctx.close()
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
