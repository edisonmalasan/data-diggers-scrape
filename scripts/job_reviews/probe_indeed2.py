"""Dump embedded JSON/state from one archived Indeed PH review page."""
import json
import re
import sys
import time

import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
URL = sys.argv[1] if len(sys.argv) > 1 else (
    "https://web.archive.org/web/20260422101955id_/"
    "https://ph.indeed.com/cmp/Coaqua-Na,-Inc./reviews"
)

for attempt in range(6):
    try:
        r = requests.get(URL, headers=H, timeout=120)
        break
    except Exception as e:  # noqa: BLE001
        print(f"attempt {attempt}: {e}")
        time.sleep(8)
else:
    sys.exit("failed to fetch")

t = r.text
print("status", r.status_code, "len", len(t))

# where does 'pros'/'review' appear (case-insensitive)?
for key in ["pros", "cons", "reviewResponse", "locations", "jobTitle", "formattedDate",
            "attribute", "rating", "__INITIAL", "initialState", "cmpData"]:
    idxs = [m.start() for m in re.finditer(re.escape(key), t, re.I)]
    print(f"{key}: {len(idxs)} hits")
    for i in idxs[:2]:
        print("   ...", re.sub(r"\s+", " ", t[max(0, i - 120):i + 240])[:360])

# extract script blobs and try JSON.parse-ish detection
scripts = re.findall(r"<script[^>]*>(.*?)</script>", t, re.S)
print("scripts:", len(scripts))
for i, s in enumerate(scripts):
    if re.search(r"pros|review", s, re.I) and len(s) > 500:
        print(f"--- script {i} len={len(s)} head:", s[:300].replace("\n", " "))
        open(r"scripts\job_reviews\.storage\indeed_script.txt", "w", encoding="utf-8").write(s)
        print("saved to .storage/indeed_script.txt")
        break
