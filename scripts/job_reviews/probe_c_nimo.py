"""Probe C-5: mynimo.com — plain requests. robots, home, review/company links."""
from __future__ import annotations

import re
import time

import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
     "Accept-Language": "en-US,en;q=0.9"}


def P(*a):
    print(" ".join(str(y) if isinstance(y, (int, float)) else ascii(str(y))
                   for y in a))


def g(u, timeout=35):
    try:
        r = requests.get(u, headers=H, timeout=timeout, allow_redirects=True)
        return r
    except Exception as e:
        P("ERR", u, type(e).__name__)
        return None


for u in ["https://mynimo.com/robots.txt",
          "https://www.mynimo.com/robots.txt"]:
    r = g(u)
    if r is None:
        continue
    P("== ", u, r.status_code, len(r.text))
    P(ascii(r.text[:2000]))
    if r.status_code == 200 and "Disallow" in r.text:
        break
    time.sleep(2.5)

time.sleep(2.5)
r = g("https://mynimo.com/")
if r is not None:
    t = r.text
    P("HOME", r.status_code, len(t), r.url)
    m = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)
    P("title:", m.group(1).strip()[:150] if m else None)
    links = set(re.findall(r'href="([^"]+)"', t))
    intr = sorted(l for l in links if re.search(r"review|compan|rating|emple|opin", l, re.I))
    P("links:", len(links), "interesting:", len(intr))
    for l in intr[:30]:
        P("   ", l[:160])
    for kw in ("review", "Review", "Pros", "Cons", "rating", "Rating", "Job Title"):
        n = t.count(kw)
        if n:
            P("kw", kw, n)

time.sleep(2.5)
r = g("https://mynimo.com/sitemap.xml")
if r is not None:
    P("SITEMAP", r.status_code, len(r.text))
    P(ascii(r.text[:1500]))
P("DONE")
