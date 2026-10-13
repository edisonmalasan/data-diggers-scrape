"""Enumerate ALL 2026 Wayback snapshots of Glassdoor /Reviews/ pages (CDX pagination)."""
import json
import time
from pathlib import Path

import requests

H = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
CDX = "https://web.archive.org/cdx/search/cdx"
OUT = Path(__file__).resolve().parents[1] / ".storage" / "glassdoor_urls.json"
BASE = {
    "url": "www.glassdoor.com/Reviews/", "matchType": "prefix",
    "from": "20260101", "to": "20261008",
    "filter": ["statuscode:200"],
    "collapse": "urlkey", "fl": "original,timestamp",
}

# page count (showNumPages does not accept collapse/fl — strip them for this call)
base_count = {k: v for k, v in BASE.items() if k not in ("collapse", "fl")}
r = requests.get(CDX, params={**base_count, "showNumPages": "true"}, headers=H, timeout=180)
npages = int(r.text.strip() or 0)
print("pages:", npages)

seen: dict[str, str] = {}
for pg in range(npages):
    for attempt in range(3):
        try:
            r = requests.get(CDX, params={**BASE, "page": str(pg)}, headers=H, timeout=180)
            rows = [l.split(None, 1) for l in r.text.splitlines() if l.strip()]
            if r.status_code == 200:
                for orig, ts in rows:
                    if orig not in seen or ts > seen[orig]:
                        seen[orig] = ts
                print(f"page {pg}: +{len(rows)} (total {len(seen)})")
                break
        except Exception as e:  # noqa: BLE001
            print(f"page {pg} attempt {attempt}: {e}")
            time.sleep(3)
    time.sleep(0.4)

OUT.write_text(json.dumps(
    [{"url": u, "ts": t} for u, t in sorted(seen.items())], indent=0), encoding="utf-8")
print("SAVED", len(seen), "->", OUT)
