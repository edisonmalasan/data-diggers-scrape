"""Site-group A probe 9: guessed profile/review paths (requests)."""
import re
import time

import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}

def probe(u, label=""):
    try:
        r = requests.get(u, headers=H, timeout=45, allow_redirects=True)
        m = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.S | re.I)
        t = (m.group(1).strip()[:90] if m else "")
        low = r.text.lower()
        print(f"{label or u} -> {r.status_code} {r.url[:95]} | {t}")
        print("    kws:", {k: low.count(k) for k in ("review", "rating", "write a review")})
    except Exception as e:  # noqa: BLE001
        print(label or u, "ERR", type(e).__name__, str(e)[:90])
    time.sleep(3)

print("--- monster guessed profiles ---")
for slug in ["accenture", "google", "ibm", "cognizant"]:
    probe(f"https://www.monster.com/company/{slug}")

print("--- talenttribe possible review routes ---")
for p in ["/reviews", "/companies/shopee/reviews", "/salary", "/salaries"]:
    probe("https://talenttribe.asia" + p)

print("--- foundit guessed company/review routes ---")
for p in ["/company/accenture", "/companies", "/reviews", "/employer-reviews"]:
    probe("https://www.foundit.com.ph" + p)
print("DONE")
