"""Phase 13: thelayoff — direct thread navigation now that CF passed in this profile."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from siteb_lib import STORAGE  # noqa: E402

PROFILE = STORAGE / "browser_profile_disc_h"


def main() -> int:
    from playwright.sync_api import sync_playwright

    threads = ["https://www.thelayoff.com/t/1m2nh0jde", "https://www.thelayoff.com/t/1kthhqv0x"]
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), channel="chrome", headless=False, locale="en-US",
            viewport={"width": 1366, "height": 900},
        )
        page = ctx.new_page()
        for i, url in enumerate(threads, 1):
            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
            except Exception as e:  # noqa: BLE001
                print("   goto ERR", type(e).__name__, e, flush=True)
            page.wait_for_timeout(12000)
            html = page.content()
            (STORAGE / f"pw_lo_thread{i}.html").write_text(html, encoding="utf-8")
            m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
            t = re.sub(r"\s+", " ", m.group(1)).strip() if m else "?"
            print(f"--- thread{i}: {page.url} title={t[:80]!r}", flush=True)
            if "Just a moment" in t:
                page.wait_for_timeout(20000)
                html = page.content()
                (STORAGE / f"pw_lo_thread{i}.html").write_text(html, encoding="utf-8")
                m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
                t = re.sub(r"\s+", " ", m.group(1)).strip() if m else "?"
                print(f"    retry title={t[:80]!r}", flush=True)
            if "Just a moment" not in t:
                body = page.inner_text("body")
                (STORAGE / f"pw_lo_thread{i}.txt").write_text(body, encoding="utf-8")
                print("BODY[:1200]:", repr(body[:1200]), flush=True)
                # metadata greps
                for kw in ("Philippines", "Manila", "job title", "Title:", "Location",
                           "Software Engineer", "works at"):
                    print(f"    kw {kw!r}: {html.lower().count(kw.lower())}", flush=True)
                break
        ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
