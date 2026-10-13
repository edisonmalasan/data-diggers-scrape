"""Phase 9: WTTJ employer profile content check + thelayoff cooldown retry."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402


def wttj() -> None:
    f = Fetcher("wttjuk")
    home = (STORAGE / "wttjuk_home.html").read_text(encoding="utf-8", errors="replace")
    links = sorted(set(re.findall(r'href="(https://app\.welcometothejungle\.com/companies/[^"]+)"', home)))
    print("WTTJ app company links:", len(links), links[:5])
    # companies sitemap: any PH entity at all?
    r0 = f.get("https://app.welcometothejungle.com/companies-sitemap",
               allow="application/xml,text/html,*/*",
               stream_to=STORAGE / "wttj_companies_sitemap.xml")
    txt = r0.text
    urls = re.findall(r"<loc>(.*?)</loc>", txt)
    print("WTTJ companies sitemap:", r0.status_code, "urls:", len(urls))
    ph = [u for u in urls if re.search(r"philippin|manila|-ph\b", u, re.I)]
    print("  PH-looking entries:", len(ph), ph[:5])
    if links:
        u = links[0].split("?")[0]
        r = f.get(u, stream_to=STORAGE / "wttj_employer.html")
        m = re.search(r"<title>(.*?)</title>", r.text, re.S | re.I)
        plain = re.sub(r"<[^>]+>", " ", r.text)
        print("WTTJ employer:", r.status_code, "| final:", r.url,
              "| title:", (m.group(1).strip()[:100] if m else "?"))
        for kw in ("Philippines", "Manila", "London", "review", "employee rating",
                   "salary", "locations"):
            print(f"   kw {kw!r}:", len(re.findall(re.escape(kw), plain, re.I)))


def layoff_retry() -> None:
    from playwright.sync_api import sync_playwright

    profile = STORAGE / "browser_profile_disc"
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(profile), channel="chrome", headless=True, locale="en-US",
            viewport={"width": 1366, "height": 900},
        )
        page = ctx.new_page()
        for url, name, wait in [
            ("https://www.thelayoff.com/accenture", "layoff_retry_company", 8000),
            ("https://www.thelayoff.com/t/1kthhqv0x", "layoff_retry_thread", 25000),
        ]:
            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
            except Exception as e:  # noqa: BLE001
                print("   goto ERR", type(e).__name__, e, flush=True)
            page.wait_for_timeout(wait)
            html = page.content()
            (STORAGE / f"pw_{name}.html").write_text(html, encoding="utf-8")
            m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
            t = (m.group(1).strip() if m else "?")[:80]
            print(f"--- {name}: {page.url} title={t!r}", flush=True)
            if "Just a moment" not in t and "moment" not in t:
                body = page.inner_text("body")
                (STORAGE / f"pw_{name}.txt").write_text(body, encoding="utf-8")
                print("   body[:700]:", repr(body[:700]), flush=True)
            else:
                print("   still on Cloudflare interstitial", flush=True)
        ctx.close()


def main() -> int:
    try:
        wttj()
    except StopSite as e:
        print("wttj STOPPED", e)
    except Exception as e:  # noqa: BLE001
        print("wttj ERROR", type(e).__name__, e)
    if len(sys.argv) > 1 and sys.argv[1] == "layoff":
        try:
            layoff_retry()
        except Exception as e:  # noqa: BLE001
            print("layoff ERROR", type(e).__name__, e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
