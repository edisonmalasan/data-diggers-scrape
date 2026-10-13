"""Phase 14: thelayoff — one last long-wait attempt on a thread page (no CAPTCHA
solving; only waiting to see whether the managed challenge auto-passes)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from siteb_lib import STORAGE  # noqa: E402

PROFILE = STORAGE / "browser_profile_disc_h"


def main() -> int:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), channel="chrome", headless=False, locale="en-US",
            viewport={"width": 1366, "height": 900},
        )
        page = ctx.new_page()
        try:
            page.goto("https://www.thelayoff.com/t/1m2nh0jde", timeout=45000,
                      wait_until="domcontentloaded")
        except Exception as e:  # noqa: BLE001
            print("goto ERR", type(e).__name__, e, flush=True)
        for i in range(6):
            page.wait_for_timeout(10000)
            html = page.content()
            m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
            t = re.sub(r"\s+", " ", m.group(1)).strip() if m else "?"
            print(f"[{(i + 1) * 10}s] title={t[:70]!r} len={len(html)} "
                  f"turn={html.lower().count('verify you are human')}", flush=True)
            if "Just a moment" not in t:
                (STORAGE / "pw_lo_thread_pass.html").write_text(html, encoding="utf-8")
                body = page.inner_text("body")
                (STORAGE / "pw_lo_thread_pass.txt").write_text(body, encoding="utf-8")
                print("PASSED. BODY[:1500]:", repr(body[:1500]), flush=True)
                break
        else:
            html = page.content()
            (STORAGE / "pw_lo_thread_last.html").write_text(html, encoding="utf-8")
            print("did not auto-pass within 60s -> CF wall", flush=True)
        ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
