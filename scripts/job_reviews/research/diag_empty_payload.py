"""Inspect raw payloads of ph/www pages that extracted items=0.

Goal: confirm whether reviewsList.items is genuinely empty or nested
differently (silent extraction loss).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
STORAGE = HERE / ".storage"

from scrape_indeed_wb import extract_items  # noqa: E402
from scrape_indeed_wb2 import archive_get, polite, resolve_latest  # noqa: E402

LATEST = STORAGE / "indeed_wb_latest.json"

PAGES = [
    "https://ph.indeed.com/cmp/Coherent-Corp.-1/reviews?fjobtitle=Quality+Assurance+Engineer",
    "https://ph.indeed.com/cmp/Lone-Star-Markets/reviews?fjobtitle=Operations+Analyst",
    "https://ph.indeed.com/cmp/Lone-Star-Markets/reviews",
    "https://www.indeed.com/cmp/Academian/reviews?fjobtitle=Software+Architect&fcountry=US&floc=Remote",
]


def main() -> int:
    latest = json.loads(LATEST.read_text(encoding="utf-8"))
    for url in PAGES:
        ts = latest.get(url)
        if not ts:
            status, ts = resolve_latest(url, latest)
            print(f"  resolve_latest -> {status} {ts}")
        print(f"\n===== {url[:110]} ts={ts} =====")
        if not ts:
            print("  no cached ts")
            continue
        r = archive_get(f"https://web.archive.org/web/{ts}id_/{url}",
                        tries=3, timeout=120)
        if r is None or r.status_code != 200:
            print(f"  fetch fail {None if r is None else r.status_code}")
            continue
        items = extract_items(r.text)
        print(f"  extract_items -> {None if items is None else len(items)}")
        m = re.search(r'<script[^>]*id="comp-initialData"[^>]*>(.*?)</script>',
                      r.text, re.S)
        if not m:
            print("  NO comp-initialData script!")
            # look for other script ids
            ids = re.findall(r'<script[^>]*id="([^"]+)"', r.text)
            print(f"  script ids present: {ids[:20]}")
            polite()
            continue
        try:
            data = json.loads(m.group(1))
        except Exception as e:  # noqa: BLE001
            print(f"  JSON parse fail: {e}")
            polite()
            continue
        print(f"  top-level keys: {sorted(data.keys())}")
        rl = data.get("reviewsList")
        if isinstance(rl, dict):
            print(f"  reviewsList keys: {sorted(rl.keys())}")
            for k, v in rl.items():
                if isinstance(v, list):
                    print(f"    list {k}: len={len(v)}")
                elif isinstance(v, dict):
                    print(f"    dict {k}: keys={sorted(v.keys())[:12]}")
                else:
                    sv = str(v)
                    print(f"    {k}: {sv[:80]}")
        else:
            print(f"  reviewsList: {type(rl).__name__} {str(rl)[:100]}")
        polite()


if __name__ == "__main__":
    raise SystemExit(main())
