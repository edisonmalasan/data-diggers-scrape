"""Phase 28: Blind — find a location value format that filters the country key."""
from __future__ import annotations

import sys
from urllib.parse import quote
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from blind_extract import extract_reviews, extract_total  # noqa: E402
from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402

BASE = "https://www.teamblind.com/company/Accenture/reviews?location="


def main() -> int:
    f = Fetcher("blind")
    tests = [
        "Philippines, ",
        "Philippines,Philippines",
        "Philippines, PH",
        "Philippines, Metro Manila",
        "Manila, Philippines",
        "philippines",
    ]
    try:
        for val in tests:
            u = BASE + quote(val, safe="")
            r = f.get(u, timeout=30)
            rs = extract_reviews(r.text)
            locs = sorted({x.get("memberLocation") or "?" for x in rs})
            tot = extract_total(r.text)
            ok = "PH" if any(x.get("memberLocationCountryIsoCode") == "PH" for x in rs) else "-"
            print(f"val={val!r}: total={tot} n={len(rs)} PH={ok} locs={locs[:5]}")
            if tot == 4 or ok == "PH":
                (STORAGE / "blind_acc_ph_hit.html").write_text(r.text, encoding="utf-8")
                print("   -> saved hit page")
                break
    except StopSite as e:
        print("STOPPED", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
