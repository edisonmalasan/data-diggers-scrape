"""Probe C-5b: mynimo — sitemapindex + look for company/review sections."""
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


r = g("https://www.mynimo.com/sitemapindex.xml")
if r is not None:
    P("SITEMAPINDEX", r.status_code, len(r.text))
    P(ascii(r.text[:3000]))
    locs = re.findall(r"<loc>(.*?)</loc>", r.text)
    P("locs:", len(locs))
    for l in locs:
        P("  ", l)
    # fetch a couple of child sitemaps looking for company/review paths
    for l in locs[:6]:
        time.sleep(2.5)
        rr = g(l)
        if rr is None:
            continue
        P("child", l, rr.status_code, len(rr.text))
        kids = re.findall(r"<loc>(.*?)</loc>", rr.text)
        P("  kids:", len(kids))
        rev = [k for k in kids if re.search(r"review|compan|rating|opin", k, re.I)]
        P("  reviewish:", len(rev))
        for k in rev[:15]:
            P("    ", k)
        for k in kids[:5]:
            P("    sample", k)
P("DONE")
