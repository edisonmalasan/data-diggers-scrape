"""Phase 4: Playwright pass for the JS/protected sites
(thelayoff, fishbowl, blind, wellfound). Own profile dir, headless preferred."""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from siteb_lib import STORAGE, UA  # noqa: E402

PROFILE = STORAGE / "browser_profile_disc"


def snap(page, name: str) -> str:
    html = page.content()
    (STORAGE / f"pw_{name}.html").write_text(html, encoding="utf-8")
    m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    title = m.group(1).strip() if m else "?"
    body = ""
    try:
        body = page.inner_text("body")[:400]
    except Exception:  # noqa: BLE001
        pass
    print(f"--- {name}: url={page.url} title={title[:90]!r}", flush=True)
    print(f"    body[:200]={body[:200]!r}", flush=True)
    return html


def main() -> int:
    PROFILE.mkdir(parents=True, exist_ok=True)
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

        # 1) thelayoff company page
        go("https://www.thelayoff.com/accenture", 5000)
        h = snap(page, "layoff_accenture")
        tlinks = sorted(set(re.findall(r'href="(/t/[^"]+|https://www\.thelayoff\.com/t/[^"]+)"', h)))
        print("    layoff thread links:", len(tlinks), tlinks[:8], flush=True)
        dates = sorted(set(re.findall(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+20\d{2}\b", h)))
        print("    layoff dates:", dates[:15], "| 2026 count:", h.count("2026"), flush=True)

        # 2) blind home + company page guess
        go("https://www.teamblind.com/", 5000)
        hb = snap(page, "blind_home")
        blinks = sorted(set(re.findall(r'href="(https?://[^"]*teamblind\.com/[^"]*)"', hb)))
        print("    blind links sample:", blinks[:15], flush=True)

        # 3) fishbowl home
        go("https://www.fishbowlapp.com/", 5000)
        hf = snap(page, "fishbowl_home")
        flinks = sorted(set(re.findall(r'href="([^"]+)"', hf)))[:40]
        print("    fishbowl links sample:", flinks[:25], flush=True)

        # 4) wellfound company page (Security Check earlier)
        go("https://wellfound.com/company/stripe", 6000)
        hw = snap(page, "wellfound_company_stripe")
        print("    wellfound 'review' mentions:", len(re.findall(r"review", hw, re.I)), flush=True)

        ctx.close()
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
