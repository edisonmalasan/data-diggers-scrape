"""Phase 7: (a) thelayoff thread via click-through, (b) Blind + Wellfound headed try."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from siteb_lib import STORAGE, UA  # noqa: E402

PROFILE = STORAGE / "browser_profile_disc"
PROFILE2 = STORAGE / "browser_profile_disc_h"


def snap(page, name: str) -> str:
    html = page.content()
    (STORAGE / f"pw_{name}.html").write_text(html, encoding="utf-8")
    m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    print(f"--- {name}: url={page.url} title={(m.group(1).strip() if m else '?')[:90]!r}",
          flush=True)
    return html


def run_headless_clickthrough() -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), channel="chrome", headless=True, locale="en-US",
            user_agent=UA, viewport={"width": 1366, "height": 900},
        )
        page = ctx.new_page()
        try:
            page.goto("https://www.thelayoff.com/accenture", timeout=45000,
                      wait_until="domcontentloaded")
        except Exception as e:  # noqa: BLE001
            print("   goto ERR", e, flush=True)
        page.wait_for_timeout(6000)
        try:
            page.click("a.thread-link", timeout=10000)
            page.wait_for_timeout(12000)
        except Exception as e:  # noqa: BLE001
            print("   click ERR", type(e).__name__, e, flush=True)
        h = snap(page, "layoff_thread_click")
        if "Just a moment" not in h:
            t = page.inner_text("body")
            (STORAGE / "pw_layoff_thread_click.txt").write_text(t, encoding="utf-8")
            print("   thread txt[:800]:", repr(t[:800]), flush=True)
        else:
            page.wait_for_timeout(20000)
            h2 = snap(page, "layoff_thread_click2")
            if "Just a moment" not in h2:
                t = page.inner_text("body")
                (STORAGE / "pw_layoff_thread_click.txt").write_text(t, encoding="utf-8")
                print("   thread txt[:800]:", repr(t[:800]), flush=True)
        ctx.close()


def run_headed() -> None:
    from playwright.sync_api import sync_playwright

    PROFILE2.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE2), channel="chrome", headless=False, locale="en-US",
            viewport={"width": 1366, "height": 900},
        )
        page = ctx.new_page()

        def go(url: str, wait: int = 8000) -> str:
            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
            except Exception as e:  # noqa: BLE001
                print("   goto ERR", type(e).__name__, e, flush=True)
            page.wait_for_timeout(wait)
            return page.content()

        h = go("https://www.teamblind.com/", 10000)
        hh = snap(page, "blind_home_headed")
        if "Something went wrong" in hh:
            page.wait_for_timeout(8000)
            hh = snap(page, "blind_home_headed2")
        print("   blind body[:400]:", repr(page.inner_text("body")[:400]), flush=True)

        h = go("https://www.teamblind.com/company/Google", 10000)
        hb = snap(page, "blind_company_headed")
        tb = page.inner_text("body")
        (STORAGE / "pw_blind_company_headed.txt").write_text(tb, encoding="utf-8")
        print("   blind company txt[:600]:", repr(tb[:600]), flush=True)

        h = go("https://wellfound.com/company/stripe", 12000)
        hw = snap(page, "wf_company_headed")
        if "Just a moment" in hw:
            page.wait_for_timeout(15000)
            hw = snap(page, "wf_company_headed2")
        tw = page.inner_text("body")
        (STORAGE / "pw_wf_company_headed.txt").write_text(tw, encoding="utf-8")
        print("   wf txt[:600]:", repr(tw[:600]), flush=True)

        ctx.close()


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("click", "both"):
        try:
            run_headless_clickthrough()
        except Exception as e:  # noqa: BLE001
            print("clickthrough FAIL", type(e).__name__, e, flush=True)
    if which in ("headed", "both"):
        try:
            run_headed()
        except Exception as e:  # noqa: BLE001
            print("headed FAIL", type(e).__name__, e, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
