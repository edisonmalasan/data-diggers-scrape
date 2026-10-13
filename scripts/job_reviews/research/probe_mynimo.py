"""Quick mynimo.com check: robots, homepage, review/corporate pages."""
import re
import time

import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/131.0.0.0 Safari/537.36"}


def get(u):
    try:
        r = requests.get(u, headers=H, timeout=30)
        print(f"GET {u} -> {r.status_code} len={len(r.text)}")
        return r
    except Exception as e:  # noqa: BLE001
        print(f"GET {u} ERR {type(e).__name__}")
        return None


r = get("https://www.mynimo.com/robots.txt")
if r is not None and r.ok:
    print(r.text[:400])
time.sleep(2)

h = get("https://www.mynimo.com/")
if h is not None and h.ok:
    t = h.text
    m = re.search(r"<title[^>]*>(.*?)</title>", t, re.S)
    print("title:", (m.group(1) if m else "?")[:80])
    hrefs = sorted(set(re.findall(r'href="(/[^"]{2,60})"', t)))
    hits = [x for x in hrefs
            if re.search(r"review|compan|empleador|employer", x, re.I)]
    print("total hrefs:", len(hrefs), "| reviewish:", hits[:15])
    for kw in ("review", "Review", "2026", "Pros", "Cons", "rating"):
        print(f"  kw {kw!r}:", t.count(kw))
time.sleep(2)

r2 = get("https://www.mynimo.com/sitemap.xml")
if r2 is not None and r2.ok:
    locs = re.findall(r"<loc>(.*?)</loc>", r2.text)
    print("sitemap locs:", len(locs), "sample:", locs[:6])
    print("reviewish locs:",
          [u for u in locs if re.search(r"review|compan", u, re.I)][:8])
