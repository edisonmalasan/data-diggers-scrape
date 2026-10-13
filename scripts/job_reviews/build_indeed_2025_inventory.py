"""Build the 2025-capture inventory for the Indeed Wayback pass.

Same page filters as the 2026 build (ph.indeed.com/cmp/ + www review pages),
but the CDX window is 2025-01-01..2025-12-31: those snapshots show 2025
reviews as their newest content — inventory the 2026 pass never touched.
Output feeds `scrape_indeed_wb2.py --year 2025` (state: queue4/done4).
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from scrape_indeed_wb import cdx_query  # noqa: E402 — shared retry/CDX logic

STORAGE = HERE / ".storage"
OUT = STORAGE / "indeed_wb_urls_2025.json"
WIN = {"from": "20250101", "to": "20251231"}

rows: dict[tuple[str, str], dict] = {}


def add(cols: list[str], host: str) -> None:
    if len(cols) < 2:
        return
    orig, ts = cols[0], cols[1]
    low = orig.lower()
    if "/-/s/assets" in low or low.endswith((".js", ".css", ".png", ".svg")):
        return
    if "/reviews" not in low:
        return
    rows[(orig, ts)] = {"url": orig, "ts": ts, "host": host}


print("[enum-2025] ph.indeed.com/cmp/ ...", flush=True)
for cols in cdx_query({"url": "ph.indeed.com/cmp/", **WIN}):
    add(cols, "ph.indeed.com")
time.sleep(2.5)

print("[enum-2025] www.indeed.com/cmp/ (review pages) ...", flush=True)
got = cdx_query({"url": "www.indeed.com/cmp/",
                 "filter": ["statuscode:200", "mimetype:text/html",
                            "original:.*/reviews.*"],
                 **WIN})
if got:
    for cols in got:
        add(cols, "www.indeed.com")
else:
    print("[enum-2025] full-prefix query empty -> per-letter fallback",
          flush=True)
    for letter in "abcdefghijklmnopqrstuvwxyz0123456789":
        for cols in cdx_query({"url": f"www.indeed.com/cmp/{letter}", **WIN}):
            if "/reviews" in cols[0].lower():
                add(cols, "www.indeed.com")
        time.sleep(2.5)

items = list(rows.values())
OUT.write_text(json.dumps({
    "created": datetime.now(timezone.utc).isoformat(),
    "window": WIN,
    "items": items,
}, indent=1), encoding="utf-8")
n_ph = sum(1 for i in items if i["host"] == "ph.indeed.com")
print(f"[enum-2025] wrote {len(items)} captures "
      f"(ph.indeed.com={n_ph}) -> {OUT.name}")
