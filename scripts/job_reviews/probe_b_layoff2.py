"""Phase 12: thelayoff retry (headed real Chrome) — get ONE thread view to check
whether posts expose job title / location at all."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from siteb_lib import STORAGE  # noqa: E402

PROFILE = STORAGE / "browser_profile_disc_h"


def main() -> int:
    PROFILE.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), channel="chrome", headless=False, locale="en-US",
            viewport={"width": 1366, "height": 900},
        )
        page = ctx.new_page()

        def dump(name: str) -> str:
            html = page.content()
            (STORAGE / f"pw_{name}.html").write_text(html, encoding="utf-8")
            m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
            t = re.sub(r"\s+", " ", m.group(1)).strip() if m else "?"
            print(f"--- {name}: {page.url} title={t[:80]!r}", flush=True)
            return html

        def go(url: str, wait: int) -> str:
            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
            except Exception as e:  # noqa: BLE001
                print("   goto ERR", type(e).__name__, e, flush=True)
            page.wait_for_timeout(wait)
            return dump(name)

        # company page
        name = "lo_headed_company"
        h = go("https://www.thelayoff.com/accenture", 15000)
        if "Just a moment" in h:
            page.wait_for_timeout(20000)
            h = dump("lo_headed_company2")

        if "Just a moment" not in h:
            # click into a thread
            try:
                page.click("a.thread-link", timeout=10000)
                page.wait_for_timeout(15000)
                name = "lo_headed_thread"
                h = dump("lo_headed_thread")
                if "Just a moment" in h:
                    page.wait_for_timeout(20000)
                    h = dump("lo_headed_thread2")
                if "Just a moment" not in h:
                    body = page.inner_text("body")
                    (STORAGE / "pw_lo_headed_thread.txt").write_text(body, encoding="utf-8")
                    print("THREAD BODY[:900]:", repr(body[:900]), flush=True)
            except Exception as e:  # noqa: BLE001
                print("   click ERR", type(e).__name__, e, flush=True)

        ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
