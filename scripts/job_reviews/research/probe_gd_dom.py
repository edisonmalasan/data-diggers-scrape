"""Step 4: map review DOM structure inside archived Glassdoor pages."""
import re
import sys
import requests
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}

# a page-2 capture of Accenture (fresh capture 2026-07-31 => many 2026 reviews)
TARGETS = [
    ("https://web.archive.org/web/20260731174615id_/https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138_P2.htm",
     "accenture-p2"),
    ("https://web.archive.org/web/20260204115946id_/https://www.glassdoor.com/Reviews/Accenture-Reviews-E4138.htm",
     "accenture-p1"),
]

for url, tag in TARGETS:
    r = requests.get(url, headers=H, timeout=120)
    t = r.text
    print(f"\n===== {tag}: status={r.status_code} len={len(t)}")
    soup = BeautifulSoup(t, "lxml")

    # find common Glassdoor review containers
    candidates = {}
    for sel in ["li[data-review]", "div[data-review]", "div.gdReview", "div[class*=Review]",
                "article", "div[id^=Review]", "div[data-test=review]"]:
        try:
            els = soup.select(sel)
        except Exception:
            els = []
        if els:
            candidates[sel] = len(ells) if False else len(els)
    print("containers:", candidates)

    # Heuristic: elements holding "Pros" and "Cons" text
    blocks = [d for d in soup.find_all(["li", "div", "article"])
              if len(d.get("class") or []) > 0
              and "Pros" in d.get_text()[:4000] and "Cons" in d.get_text()[:4000]]
    # pick smallest such blocks (deepest)
    print("blocks w/ Pros+Cons:", len(blocks))
    if blocks:
        b = min(blocks, key=lambda x: len(x.get_text()))
        print("smallest block classes:", b.get("class"), "id:", b.get("id"))
        txt = " ".join(b.get_text(" ", strip=True).split())
        print("TEXT SAMPLE:", txt[:1200])

        # inspect child structure
        for child in b.find_all(recursive=False)[:14]:
            print("   child:", child.name, child.get("class"), "->",
                  " ".join(child.get_text(" ", strip=True).split())[:140])
