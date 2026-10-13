"""Phase 30: Blind — inspect IN-filtered list; test country filter threshold (AU vs JP)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from blind_extract import extract_reviews, flight_strings  # noqa: E402
from siteb_lib import STORAGE, Fetcher, StopSite  # noqa: E402
import re


def filtered(h: str) -> tuple[int, int]:
    blob = "\n".join(flight_strings(h))
    m = re.search(r'"filteredCount":(\d+),"totalCount":(\d+)', blob)
    return (int(m.group(1)), int(m.group(2))) if m else (-1, -1)


def main() -> int:
    h = (STORAGE / "blind_acc_IN.html").read_text(encoding="utf-8", errors="replace")
    rs = extract_reviews(h)
    print("IN-filtered list:")
    for x in rs[:12]:
        print("   ", x.get("memberLocation"), "|", x.get("memberLocationCountryIsoCode"),
              "|", x.get("jobgroup"))
    print("filtered/total:", filtered(h))

    f = Fetcher("blind")
    tests = [
        ("AU", "https://www.teamblind.com/company/Accenture/reviews?location=AU"),
        ("JP", "https://www.teamblind.com/company/Accenture/reviews?location=JP"),
        ("MX", "https://www.teamblind.com/company/Accenture/reviews?location=MX"),
    ]
    try:
        for code, u in tests:
            r = f.get(u, timeout=30, stream_to=STORAGE / f"blind_acc_{code}.html")
            fc, tc = filtered(r.text)
            rs2 = extract_reviews(r.text)
            iso = sorted({x.get("memberLocationCountryIsoCode") for x in rs2})
            print(f"location={code}: filtered={fc} total={tc} iso_in_list={iso}")
    except StopSite as e:
        print("STOPPED", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
