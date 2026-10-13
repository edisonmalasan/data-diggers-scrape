"""Probe D-1 (discovery): nodeflair.com — plain requests accessibility + review fields.

NodeFlair = Asia tech careers platform (SG/MY/TH/ID/PH) with company reviews
(salaries, reviews, interviews). Check robots, company page structure, and
whether reviews expose date / job title / location / pros+cons text.
"""
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
    for attempt in range(4):
        try:
            r = requests.get(u, headers=H, timeout=timeout, allow_redirects=True)
            if r.status_code in (429, 500, 502, 503, 504):
                P("  backoff", r.status_code, u)
                time.sleep(min(3 * 2 ** attempt, 60))
                continue
            return r
        except Exception as e:
            P("  ERR", type(e).__name__, u)
            time.sleep(min(3 * 2 ** attempt, 60))
    return None


r = g("https://nodeflair.com/robots.txt")
if r is not None:
    P("ROBOTS", r.status_code, len(r.text))
    P(ascii(r.text[:2500]))

time.sleep(2.5)
r = g("https://nodeflair.com/")
if r is not None:
    t = r.text
    P("\nHOME", r.status_code, len(t), r.url)
    m = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)
    P("title:", m.group(1).strip()[:150] if m else None)
    links = sorted(set(re.findall(r'href="([^"]+)"', t)))
    intr = [l for l in links if re.search(r"compan|review", l, re.I)]
    P("links:", len(links), "company/review-ish:", len(intr))
    for l in intr[:20]:
        P("   ", l[:160])

time.sleep(2.5)
for u in ["https://nodeflair.com/most-popular-companies-list",
          "https://nodeflair.com/companies/nodeflair"]:
    rr = g(u)
    if rr is None:
        P("FAIL", u)
        continue
    tt = rr.text
    P("\nPAGE", u, rr.status_code, len(tt))
    m = re.search(r"<title[^>]*>(.*?)</title>", tt, re.S | re.I)
    P("title:", m.group(1).strip()[:150] if m else None)
    for kw in ("review", "Review", "Pros", "Cons", "Rating", "rating",
               "Philippines", "Job Title", "Current employee", "benefits"):
        n = tt.count(kw)
        if n:
            P("  kw", kw, n)
    clinks = sorted(set(re.findall(r'href="(/companies/[^"?#]+)"', tt)))
    P("  company links:", len(clinks), "sample:", clinks[:8])
    time.sleep(2.5)

P("DONE")
