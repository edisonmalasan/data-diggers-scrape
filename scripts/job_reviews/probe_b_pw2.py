"""Phase 5: deeper structure — thelayoff thread, fishbowl company/posts, blind retry."""
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

        # 1) thelayoff thread page -> post metadata
        go("https://www.thelayoff.com/t/1m2fyv8aq", 5000)
        h = snap(page, "layoff_thread1")
        # look for author/role/location markers
        for pat in [r'class="[^"]*author[^"]*"', r'class="[^"]*username[^"]*"',
                    r'class="[^"]*location[^"]*"', r'class="[^"]*title[^"]*"',
                    r'data-user[^=]*="[^"]*"']:
            hits = sorted(set(re.findall(pat, h, re.I)))
            if hits:
                print(f"    pat {pat}: {hits[:6]}", flush=True)
        body = page.inner_text("body")
        (STORAGE / "pw_layoff_thread1.txt").write_text(body, encoding="utf-8")
        print("    thread body[:600]:", repr(body[:600]), flush=True)

        # 2) fishbowl directory of companies
        go("https://www.fishbowlapp.com/directory/companies", 5000)
        hd = snap(page, "fishbowl_dir")
        clinks = sorted(set(re.findall(r'href="(/companies/[^"]+|/company/[^"]+)"', hd)))
        print("    fishbowl company links:", len(clinks), clinks[:10], flush=True)

        # 3) fishbowl posts listing
        go("https://www.fishbowlapp.com/posts", 5000)
        hp = snap(page, "fishbowl_posts")
        plinks = sorted(set(re.findall(r'href="(/posts/[^"]+|/post/[^"]+)"', hp)))
        print("    fishbowl post links:", len(plinks), plinks[:10], flush=True)
        ptxt = page.inner_text("body")
        (STORAGE / "pw_fishbowl_posts.txt").write_text(ptxt, encoding="utf-8")
        print("    posts body[:500]:", repr(ptxt[:500]), flush=True)

        # 4) blind retry + company page guesses
        go("https://www.teamblind.com/", 6000)
        hb = snap(page, "blind_home2")
        print("    blind2 body[:300]:", repr(page.inner_text("body")[:300]), flush=True)
        for u in ["https://www.teamblind.com/company/Google",
                  "https://www.teamblind.com/companies/Google",
                  "https://www.teamblind.com/company/google/reviews"]:
            go(u, 4000)
            h2 = snap(page, "blind_" + re.sub(r"\W+", "_", u)[-40:])
            if "Something went wrong" not in h2 and "static-blockpage" not in h2:
                break

        ctx.close()
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
