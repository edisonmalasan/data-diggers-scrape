"""Enumerate Indeed PH 2026 review captures; find pages with real reviews."""
import json
import re
import time
from pathlib import Path

import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
CDX = "https://web.archive.org/cdx/search/cdx"
STORAGE = Path(__file__).resolve().parents[1] / ".storage"
STORAGE.mkdir(exist_ok=True)

# 1) full CDX list (no collapse filter on review pages only) -> save
params = {
    "url": "ph.indeed.com/cmp/", "matchType": "prefix",
    "from": "20260101", "to": "20261009",
    "filter": "statuscode:200", "collapse": "urlkey",
    "fl": "original,timestamp", "limit": "50000",
}
rows = []
for attempt in range(6):
    try:
        r = requests.get(CDX, params=params, headers=H, timeout=180)
        r.raise_for_status()
        rows = [l.split(None, 1) for l in r.text.splitlines() if l.strip()]
        break
    except Exception as e:  # noqa: BLE001
        print(f"cdx attempt {attempt}: {e}")
        time.sleep(8)

(STORAGE / "indeed_cdx.json").write_text(json.dumps(rows), encoding="utf-8")
rev = [(o, t) for o, t in rows if "/reviews" in o
       and not o.endswith((".css", ".js", ".svg", ".png", ".jpg", ".ico"))]
(STORAGE / "indeed_review_pages.json").write_text(json.dumps(rev), encoding="utf-8")
print(f"total={len(rows)} review-ish={len(rev)}")
for o, t in rev:
    print(" ", t, o[:130])

# 2) sample-fetch a few, look for embedded reviews
def find_review_json(txt: str):
    """Return (found_count, review_objs) from the page's embedded state."""
    m = re.search(r'"foundReviewCount"\s*:\s*(\d+)', txt)
    found = int(m.group(1)) if m else -1
    # look for review object markers
    has_pros = '"pros"' in txt or '"reviewResponse"' in txt
    return found, has_pros

for o, t in rev[:8]:
    snap = f"https://web.archive.org/web/{t}id_/{o}"
    ok = False
    for attempt in range(5):
        try:
            r = requests.get(snap, headers=H, timeout=120)
            txt = r.text
            found, has_pros = find_review_json(txt)
            print(f"{t} {o[:90]} -> status={r.status_code} found={found} has_pros={has_pros}")
            if has_pros:
                (STORAGE / "indeed_with_reviews.html").write_text(txt, encoding="utf-8")
                print("  SAVED page with reviews -> .storage/indeed_with_reviews.html")
                ok = True
            break
        except Exception as e:  # noqa: BLE001
            print(f"  attempt {attempt}: {e}")
            time.sleep(8)
    time.sleep(2.5)
print("DONE")
