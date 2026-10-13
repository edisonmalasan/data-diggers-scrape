"""Site-group A probe 7: CareerBuilder company directory + a profile page."""
import re
import time

import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}

def get(u):
    try:
        return requests.get(u, headers=H, timeout=45, allow_redirects=True)
    except Exception as e:  # noqa: BLE001
        print("  ERR", type(e).__name__, str(e)[:100])
        return None

r = get("https://www.careerbuilder.com/company")
print("CB /company ->", r.status_code if r else None, len(r.text) if r else 0)
if r is not None:
    hrefs = sorted(set(re.findall(r'href="(/company[^"]*)"', r.text)))
    print("company links:", len(hrefs))
    for h in hrefs[:20]:
        print("   ", h)
    kws = ("review", "rating", "employee", "write a review")
    low = r.text.lower()
    print("kws:", {k: low.count(k) for k in kws})
time.sleep(3)

# take one profile
if r is not None:
    profs = [h for h in hrefs if re.match(r"/company/[A-Za-z0-9-]+", h)
             and not re.match(r"/company$", h)]
    if profs:
        url = "https://www.careerbuilder.com" + profs[0]
        p = get(url)
        if p is not None:
            m = re.search(r"<title[^>]*>(.*?)</title>", p.text, re.S | re.I)
            print("profile:", url, "->", p.status_code,
                  "|", (m.group(1).strip()[:100] if m else ""))
            low = p.text.lower()
            print("kws:", {k: low.count(k) for k in
                           ("review", "rating", "employee", "pros", "cons")})
            # look for review sections in html
            for sel in ["review", "Reviews", "employee rating"]:
                pass
            txt = re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", " ", p.text, flags=re.S))
            txt = re.sub(r"\s+", " ", txt)
            i = low.find("review")
            print("context:", txt[max(0, i - 100): i + 400] if i >= 0 else "(no 'review' text)")
            # dates?
            print("dates:", sorted(set(re.findall(
                r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+20\d\d",
                p.text)))[:10])
time.sleep(3)

# does a reviews path exist under /company?
for path in ["/company/reviews", "/company/review"]:
    rr = get("https://www.careerbuilder.com" + path)
    if rr is not None:
        m = re.search(r"<title[^>]*>(.*?)</title>", rr.text, re.S | re.I)
        print(path, "->", rr.status_code, "|", (m.group(1).strip()[:80] if m else ""))
    time.sleep(3)
print("DONE")
