"""Probe gowork.ph LIVE (never probed before — only Wayback was checked).

Checks: robots, homepage reachability, company/review URL patterns,
field availability (job title / date / location / pros-cons), any 2026.
Plain requests only — no browser, no login.
"""
import re
import sys
import time

import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/131.0.0.0 Safari/537.36"}


def get(url, timeout=40):
    try:
        r = requests.get(url, headers=H, timeout=timeout)
        print(f"GET {url} -> {r.status_code} len={len(r.text)} "
              f"final={r.url[:90]}")
        return r
    except Exception as e:  # noqa: BLE001
        print(f"GET {url} ERR {type(e).__name__}: {e}")
        return None


def main():
    for root in ("https://gowork.ph/robots.txt",
                 "https://www.gowork.ph/robots.txt"):
        r = get(root)
        if r is not None and r.ok:
            print(r.text[:600])
            break
        time.sleep(2)

    home = get("https://gowork.ph/")
    time.sleep(2)
    if home is None or not home.ok:
        home = get("https://www.gowork.ph/")
        time.sleep(2)
    if home is None or not home.ok:
        print("HOME UNREACHABLE — gowork.ph dead")
        return 1

    html = home.text
    print("title:", (re.search(r"<title[^>]*>(.*?)</title>", html,
                               re.S) or [None, "?"])[1][:100])

    # link patterns: company / review / salary pages
    hrefs = sorted(set(re.findall(r'href="(/[^"]{2,80})"', html)))
    print(f"unique internal hrefs: {len(hrefs)}")
    interesting = [h for h in hrefs
                   if re.search(r"review|compan|salary|employer|job", h, re.I)]
    print("reviewish hrefs:", interesting[:20])

    # sitemap
    for sm in ("https://gowork.ph/sitemap.xml",
               "https://www.gowork.ph/sitemap.xml"):
        r = get(sm)
        time.sleep(2)
        if r is not None and r.ok and "xml" in r.headers.get("content-type", "") \
                or (r is not None and r.ok and r.text.lstrip().startswith("<?xml")):
            locs = re.findall(r"<loc>(.*?)</loc>", r.text)
            print(f"sitemap locs: {len(locs)}; sample: {locs[:8]}")
            rev_locs = [u for u in locs if re.search(r"review|company", u, re.I)]
            print(f"review-ish sitemap locs: {len(rev_locs)}; {rev_locs[:8]}")
            break

    # keyword scan of homepage for field evidence
    for kw in ("2026", "Pros", "Cons", "review", "Review", "rating",
               "Makati", "Quezon City", "Manila"):
        print(f"  home kw {kw!r}: {html.count(kw)}")

    # probe a review-ish URL if we found one
    cand = None
    for h in interesting:
        if re.search(r"review", h, re.I):
            cand = "https://gowork.ph" + h if h.startswith("/") else h
            break
    if cand:
        time.sleep(2)
        r = get(cand)
        if r is not None and r.ok:
            t = r.text
            print("  candidate page scan:")
            for kw in ("2026", "2025", "Pros", "Cons", "Job Title",
                       "Location", "Makati", "Philippines"):
                print(f"    {kw!r}: {t.count(kw)}")
            dates = sorted(set(re.findall(r"20\d{2}-\d{2}-\d{2}", t)))
            print("    iso dates:", dates[:10])
    return 0


if __name__ == "__main__":
    sys.exit(main())
