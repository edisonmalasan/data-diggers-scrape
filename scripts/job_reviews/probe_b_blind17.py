"""Phase 33: Blind — extend 2026 coverage for Oracle / Amazon / Microsoft / Google."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from blind_extract import extract_reviews  # noqa: E402
from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402
from probe_b_blind16 import is_ph  # noqa: E402

PLAN = [
    ("Oracle", 7, 13),
    ("Amazon", 7, 21),
    ("Microsoft", 7, 27),
    ("Google", 7, 27),
]


def main() -> int:
    f = Fetcher("blind")
    cand_path = STORAGE / "blind_ph_candidates.json"
    candidates = {x["id"]: x for x in json.loads(cand_path.read_text(encoding="utf-8"))}
    scanned = 0
    try:
        for slug, a, b in PLAN:
            for page in range(a, b):
                u = f"https://www.teamblind.com/company/{slug}/reviews?page={page}"
                r = f.get(u, timeout=30)
                scanned += 1
                rs = extract_reviews(r.text)
                if not rs:
                    print(f"{slug} p{page}: no reviews parsed -> stop")
                    break
                dates = sorted((x.get("createdAt") or "")[:10] for x in rs)
                ph_here = [x for x in rs if is_ph(x)]
                print(f"{slug} p{page}: n={len(rs)} range={dates[0]}..{dates[-1]} PH={len(ph_here)}")
                for x in ph_here:
                    candidates[x["id"]] = x
                if dates[-1] < "2026-01-01":
                    print(f"   -> pre-2026 page, stop {slug}")
                    break
                if dates[0] < "2026-01-01":
                    print(f"   -> straddles 2026, stop {slug}")
                    break
    except StopSite as e:
        print("STOPPED", e)

    cand_path.write_text(json.dumps(list(candidates.values()), ensure_ascii=False, indent=1),
                         encoding="utf-8")
    print(f"scanned={scanned} PH_candidates={len(candidates)}")
    for x in candidates.values():
        print("   ", x.get("companyName"), "|", x.get("jobgroup"), "|",
              x.get("memberLocation"), "|", (x.get("createdAt") or "")[:10])
    return 0


if __name__ == "__main__":
    sys.exit(main())
