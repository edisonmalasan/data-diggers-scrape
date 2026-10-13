"""Phase 34: thelayoff — final thread attempt with a FRESH browser profile (no
CAPTCHA solving; only navigation + waiting)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from siteb_lib import STORAGE  # noqa: E402

PROFILE = STORAGE / "browser_profile_disc_tlo"


def main() -> int:
    PROFILE.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), channel="chrome", headless=True, locale="en-US",
            viewport={"width": 1366, "height": 900},
        )
        page = ctx.new_page()
        try:
            page.goto("https://www.thelayoff.com/t/1m2nh0jde", timeout=45000,
                      wait_until="domcontentloaded")
        except Exception as e:  # noqa: BLE001
            print("goto ERR", type(e).__name__, e, flush=True)
        for i in range(4):
            page.wait_for_timeout(15000)
            html = page.content()
            m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
            t = re.sub(r"\s+", " ", m.group(1)).strip() if m else "?"
            print(f"[{(i + 1) * 15}s] {t[:70]!r} len={len(html)}", flush=True)
            if "Just a moment" not in t:
                (STORAGE / "pw_tlo_thread_final.html").write_text(html, encoding="utf-8")
                body = page.inner_text("body")
                (STORAGE / "pw_tlo_thread_final.txt").write_text(body, encoding="utf-8")
                print("BODY[:1500]:", repr(body[:1500]), flush=True)
                for kw in ("Job Title", "Location", "Philippines", "Manila",
                           "works at", "Posted"):
                    print(f"   kw {kw!r}: {html.lower().count(kw.lower())}", flush=True)
                break
        else:
            print("still on Cloudflare -> documented wall", flush=True)
        ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
