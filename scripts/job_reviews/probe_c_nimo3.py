"""Probe C-5c: mynimo company-profiles — do company pages carry employee reviews?"""
from __future__ import annotations

import re
import time

import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}


def P(*a):
    print(" ".join(str(y) if isinstance(y, (int, float)) else ascii(str(y))
                   for y in a))


def g(u, timeout=35):
    try:
        return requests.get(u, headers=H, timeout=timeout, allow_redirects=True)
    except Exception as e:
        P("ERR", u, type(e).__name__)
        return None


r = g("https://www.mynimo.com/company-profiles")
if r is not None:
    t = r.text
    P("DIR", r.status_code, len(t), r.url)
    m = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)
    P("title:", m.group(1).strip()[:150] if m else None)
    for kw in ("review", "Review", "Pros", "Cons", "Rating", "rating", "stars"):
        n = t.count(kw)
        if n:
            P("kw", kw, n)
    links = sorted(set(re.findall(r'href="(/company-profiles/[^"?#]+)"', t)))
    P("company links:", len(links), "sample:")
    for l in links[:15]:
        P("   ", l)
    # follow first 2 company pages
    for l in links[:2]:
        time.sleep(2.5)
        rr = g("https://www.mynimo.com" + l)
        if rr is None:
            continue
        tt = rr.text
        P("COMPANY", l, rr.status_code, len(tt))
        m = re.search(r"<title[^>]*>(.*?)</title>", tt, re.S | re.I)
        P("  title:", m.group(1).strip()[:150] if m else None)
        for kw in ("review", "Review", "Pros", "Cons", "Rating", "rating",
                   "Job Title", "Current employee", "Former employee"):
            n = tt.count(kw)
            if n:
                P("  kw", kw, n)
        # any review-ish anchors
        ints = sorted(set(re.findall(r'href="([^"]*(?:review|rating)[^"]*)"', tt, re.I)))
        for x in ints[:10]:
            P("  link", x[:150])
P("DONE")
