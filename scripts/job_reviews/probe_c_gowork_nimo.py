"""Probe C-1: gowork.ph + mynimo.com via plain requests (accessibility first).

Checks: robots.txt, home page, link/URL structure for company & review pages,
any review markers. 2-3s politeness, backoff on 429/5xx, stop after 8 fails.
"""
from __future__ import annotations

import re
import time

import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
     "Accept-Language": "en-US,en;q=0.9"}

fails = 0
reqs = 0


def get(url: str, timeout: int = 40) -> requests.Response | None:
    global fails, reqs
    delay = 2.5
    for attempt in range(6):
        if reqs >= 120:
            return None
        try:
            reqs += 1
            r = requests.get(url, headers=H, timeout=timeout, allow_redirects=True)
            if r.status_code in (403, 429, 500, 502, 503, 504):
                fails += 1
                if fails >= 8:
                    print(f"  !! 8 consecutive hard fails -> stop ({url} {r.status_code})")
                    return None
                wait = min(delay, 60)
                print(f"  .. {r.status_code} backoff {wait}s {url}")
                time.sleep(wait)
                delay = min(delay * 2, 60)
                continue
            fails = 0
            time.sleep(2.5)
            return r
        except Exception as e:
            fails += 1
            print(f"  .. ERR {type(e).__name__} {url}")
            if fails >= 8:
                return None
            time.sleep(min(delay, 60))
            delay = min(delay * 2, 60)
    return None


def dump_site(name: str, base: str, probes: list[str]) -> None:
    print(f"\n{'=' * 70}\n### {name}  ({base})")
    for path in probes:
        url = base + path
        r = get(url)
        if r is None:
            print(f"  FAIL {url}")
            continue
        ct = r.headers.get("content-type", "")
        body = r.text
        print(f"\n  {url}\n    -> {r.status_code} {ct} len={len(body)} final={r.url}")
        if "text/html" not in ct and "xml" not in ct:
            print("    head:", repr(body[:400]))
            continue
        title = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
        print("    title:", repr(title.group(1).strip()[:120]) if title else None)
        for kw in ("review", "Review", "pros", "Pros", "cons", "Cons",
                   "rating", "Rating", "job title", "Job Title"):
            n = body.count(kw)
            if n:
                print(f"    {kw!r}: {n}")
        # link patterns
        links = set(re.findall(r'href="([^"]+)"', body))
        interesting = sorted(l for l in links
                             if re.search(r"review|company|employer|rating| opinie", l, re.I))
        print(f"    links total={len(links)} interesting={len(interesting)}")
        for l in interesting[:25]:
            print("      ", l[:160])
        if path in ("/robots.txt", "/sitemap.xml"):
            print("    --- body ---")
            print(body[:2000])


dump_site("gowork.ph", "https://gowork.ph", [
    "/robots.txt",
    "/",
    "/sitemap.xml",
])

dump_site("mynimo.com", "https://mynimo.com", [
    "/robots.txt",
    "/",
    "/sitemap.xml",
])

print("\nDONE")
