"""Inspect structure of (a) a filtered listing page and (b) a per-review permalink."""
import re
import sys
import time
from pathlib import Path

import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
STORAGE = Path(__file__).resolve().parent / ".storage"

URLS = [
    ("coherent_filtered",
     "https://web.archive.org/web/20260522010254id_/"
     "https://ph.indeed.com/cmp/Coherent-Corp.-1/reviews?fjobtitle=Quality+Assurance+Engineer&fcountry=PH"),
    ("grandapex_single",
     "https://web.archive.org/web/20260113065243id_/"
     "https://ph.indeed.com/cmp/Grand-Apex-Construction-Inc./reviews/"
     "no-benefits-and-considerations-for-employee?id=d04032f55b08e992"),
    ("keyence_single",
     "https://web.archive.org/web/20260424172508id_/"
     "https://ph.indeed.com/cmp/Keyence/reviews/good-salary?id=97c38fcba186b46a"),
]

MARKERS = ["pros", "cons", "jobTitle", "location", "rating", "formattedDate",
           "reviewResponse", "foundReviewCount", "attributeId", "language"]

for name, url in URLS:
    txt = None
    for attempt in range(6):
        try:
            r = requests.get(url, headers=H, timeout=120)
            if r.status_code == 200:
                txt = r.text
                break
            print(f"{name}: status {r.status_code}")
            break
        except Exception as e:  # noqa: BLE001
            print(f"{name} attempt {attempt}: {e}")
            time.sleep(8)
    if not txt:
        print(f"{name}: FAILED")
        continue
    (STORAGE / f"indeed_{name}.html").write_text(txt, encoding="utf-8")
    print(f"\n=== {name} len={len(txt)} saved")
    for k in MARKERS:
        hits = [m.start() for m in re.finditer(re.escape('"' + k + '"'), txt)]
        print(f"  {k}: {len(hits)}")
        for i in hits[:1]:
            print("     ...", re.sub(r"\s+", " ", txt[max(0, i - 80):i + 300])[:380])
    time.sleep(2.5)
print("\nDONE")
