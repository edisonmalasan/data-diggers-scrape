"""Phase 32: Blind — bounded page scan for PH reviews on companies known to have PH.

Stops per company at the first page whose reviews are all pre-2026 (reviews are
served recent-first), or at the per-company page cap.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from blind_extract import extract_reviews  # noqa: E402
from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402

# slug -> (known PH facet count, page cap)
TARGETS = [
    ("Accenture", 4, 6),
    ("Microsoft", 3, 6),
    ("IBM", 2, 6),
    ("Optum", 2, 8),
    ("Google", 2, 6),
    ("Citi", 1, 8),
    ("Wells-Fargo", 1, 8),
    ("JPMorgan", 1, 6),
    ("EY", 1, 6),
    ("Grab", 1, 6),
    ("Analog-Devices", 1, 6),
    ("Cisco", 1, 6),
    ("Oracle", 1, 6),
    ("Amazon", 1, 6),
    ("Manulife", 1, 1),
]

PHISH = ("philippin", "manila", "makati", "taguig", "cebu", "davao", "iloilo",
         "bgc", "pasig", "quezon", "alabang", "clark", "mandaluyong")


def is_ph(r: dict) -> bool:
    if r.get("memberLocationCountryIsoCode") == "PH":
        return True
    loc = (r.get("memberLocation") or "").lower()
    return any(k in loc for k in PHISH)


def main() -> int:
    f = Fetcher("blind")
    candidates: dict[int, dict] = {}
    scanned = 0
    try:
        for slug, ph_count, cap in TARGETS:
            for page in range(1, cap + 1):
                u = f"https://www.teamblind.com/company/{slug}/reviews?page={page}"
                r = f.get(u, timeout=30)
                scanned += 1
                rs = extract_reviews(r.text)
                if not rs:
                    print(f"{slug} p{page}: no reviews parsed")
                    break
                dates = sorted((x.get("createdAt") or "")[:10] for x in rs)
                ph_here = [x for x in rs if is_ph(x)]
                print(f"{slug} p{page}: n={len(rs)} range={dates[0]}..{dates[-1]} "
                      f"PH={len(ph_here)}")
                for x in ph_here:
                    candidates[x["id"]] = x
                # stop when this whole page is pre-2026
                if dates[-1] < "2026-01-01":
                    print(f"   -> page entirely pre-2026, stop {slug}")
                    break
                if dates[0] < "2026-01-01":
                    print(f"   -> page straddles 2026, stop {slug}")
                    break
                time.sleep(0.2)
    except StopSite as e:
        print("STOPPED", e)

    out = STORAGE / "blind_ph_candidates.json"
    out.write_text(json.dumps(list(candidates.values()), ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\nscanned_pages={scanned} PH_candidates={len(candidates)} -> {out}")
    for x in candidates.values():
        print("   ", x.get("companyName"), "|", x.get("jobgroup"), "|",
              x.get("memberLocation"), "|", (x.get("createdAt") or "")[:10],
              "|", (x.get("summary") or "")[:40])
    return 0


if __name__ == "__main__":
    sys.exit(main())
