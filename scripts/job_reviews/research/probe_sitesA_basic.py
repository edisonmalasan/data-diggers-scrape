"""Site-group A basic probe: accessibility, robots.txt, review-page hints.

Sites: talenttribe.asia, jobsdb.com, monster(.com.ph), careerbuilder(.com),
jobwiser.com. Requests only, polite 2.5s delay, no logins/CAPTCHAs.
"""
import re
import time
import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
     "Accept-Language": "en-US,en;q=0.9"}

TARGETS = [
    "https://talenttribe.asia/",
    "https://www.jobsdb.com/en-ph",
    "https://www.monster.com.ph/",
    "https://www.careerbuilder.com/",
    "https://www.careerbuilder.com.ph/",
    "https://www.jobwiser.com/",
]

def get(url, timeout=40):
    try:
        r = requests.get(url, headers=H, timeout=timeout, allow_redirects=True)
        return r
    except Exception as e:
        print(f"  ERR {type(e).__name__}: {e}")
        return None

for u in TARGETS:
    print("=" * 70)
    print("URL:", u)
    r = get(u)
    if r is None:
        continue
    print("status:", r.status_code, "-> final:", r.url)
    print("server:", r.headers.get("server", ""), "| cf:", "cloudflare" in r.headers.get("server", "").lower())
    txt = r.text[:200000]
    m = re.search(r"<title[^>]*>(.*?)</title>", txt, re.S | re.I)
    print("title:", (m.group(1).strip()[:150] if m else "(none)"))
    low = txt.lower()
    for kw in ["review", "employee review", "company review", "salary review", "captcha", "access denied", "just a moment"]:
        print(f"  kw {kw!r}: {low.count(kw)}")
    # robots.txt
    time.sleep(2.5)
    base = re.sub(r"(https://[^/]+).*", r"\1", u)
    rb = get(base + "/robots.txt")
    if rb is not None and rb.status_code == 200:
        lines = rb.text.splitlines()
        print(f"robots.txt ({len(lines)} lines):")
        for ln in lines[:40]:
            print("   ", ln)
        rev = [ln for ln in lines if "review" in ln.lower()]
        if rev:
            print("  ROBOTS review lines:", rev[:10])
    else:
        print("robots.txt:", rb.status_code if rb is not None else "ERR")
    time.sleep(2.5)
print("DONE")
