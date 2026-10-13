"""Site-group A probe 4: foundit company links + careerbuilder path checks."""
import re
import time

import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}

r = requests.get("https://www.foundit.com.ph/", headers=H, timeout=45)
links = set(re.findall(r'href="([^"]*(?:company|employer|cmp)[^"]*)"', r.text, re.I))
print("foundit company-ish links:", len(links))
for l in sorted(links)[:30]:
    print("  ", l)
time.sleep(3)

for path in ["/employers", "/employer", "/company", "/companies", "/employer-reviews",
             "/advice/company-reviews", "/reviews"]:
    try:
        rr = requests.get("https://www.careerbuilder.com" + path, headers=H,
                          timeout=40, allow_redirects=True)
        m = re.search(r"<title[^>]*>(.*?)</title>", rr.text, re.S | re.I)
        t = m.group(1).strip()[:70] if m else ""
        print("CB", path, "->", rr.status_code, rr.url[:90], "|", t)
    except Exception as e:  # noqa: BLE001
        print("CB", path, "ERR", type(e).__name__)
    time.sleep(3)
print("DONE")
